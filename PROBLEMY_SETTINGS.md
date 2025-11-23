# Analiza problemów w ustawieniach (nc/settings/dev.py)

## 🔴 Problem 1: Redis/Celery - Docker vs Lokalne

**W pliku `nc/settings/dev.py` linia 88-89:**
```python
CELERY_BROKER_URL = 'redis://:dev_password@redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://:dev_password@redis:6379/0'
```

**Problem:**
- Hostname `redis` to nazwa kontenera Docker
- Jeśli uruchamiasz agenta **lokalnie** (nie w Dockerze), nie znajdzie Redis
- Powinno być `localhost` lub `127.0.0.1` dla lokalnego uruchomienia

**Rozwiązanie:**
- Dla lokalnego: `redis://:dev_password@localhost:6379/0`
- Dla Dockera: `redis://:dev_password@redis:6379/0` (obecne)

---

## 🔴 Problem 2: Port aplikacji Django - 8080 vs 8000

**W kodzie agenta:**
- Agent używa: `http://localhost:8080` (domyślnie)
- W dokumentacji: `http://localhost:8000`
- W `update_task_with_category.py`: `base_url='http://localhost:8080'`

**Problem:**
- Jeśli Django działa na porcie **8000**, agent nie połączy się
- Jeśli Django działa na porcie **8080**, to OK

**Sprawdź:**
- Na jakim porcie działa Twoja aplikacja Django?
- `python manage.py runserver` domyślnie używa **8000**
- Jeśli używasz Nginx, może być **8080**

**Rozwiązanie:**
- Sprawdź na jakim porcie działa Django
- Zaktualizuj `base_url` w zadaniu agenta

---

## 🟡 Problem 3: CSRF/CORS - powinno działać

**W `nc/settings/dev.py`:**
- `CSRF_TRUSTED_ORIGINS` zawiera `http://localhost:8080` ✅
- `CORS_ALLOWED_ORIGINS` zawiera `http://localhost:8080` ✅
- `ALLOWED_HOSTS` zawiera `localhost` ✅

**To powinno działać**, ale sprawdź czy Django rzeczywiście działa na porcie 8080.

---

## 🔴 Problem 4: Agent nie może znaleźć tabeli produktów

**Z logów:**
```
Timeout 15000ms exceeded.
waiting for locator("table#result_list tbody tr") to be visible
```

**Możliwe przyczyny:**
1. **Nie zalogował się** - agent nie przeszedł przez logowanie
2. **Zły URL** - agent nie trafił na listę produktów
3. **Brak produktów** - lista jest pusta (ale powinien pokazać pustą tabelę)
4. **Strona się nie załadowała** - timeout

**Sprawdź:**
- Czy agent faktycznie się loguje? (sprawdź logi)
- Czy przechodzi na `/admin/matterhorn1/product/`?
- Czy są produkty w bazie dla marki Marko, kategorii "Kostiumy Dwuczęściowe"?

---

## ✅ Co naprawić:

1. **Sprawdź port Django:**
   ```bash
   # Sprawdź na jakim porcie działa Django
   netstat -ano | findstr :8000
   netstat -ano | findstr :8080
   ```

2. **Zaktualizuj Redis (jeśli lokalnie):**
   - Jeśli uruchamiasz lokalnie, zmień `redis` na `localhost` w `dev.py`

3. **Zaktualizuj base_url w zadaniu:**
   - Sprawdź na jakim porcie działa Django
   - Zaktualizuj zadanie z poprawnym URL

4. **Sprawdź logowanie agenta:**
   - Dodaj więcej logów na początku (już dodane)
   - Sprawdź czy agent przechodzi przez logowanie

