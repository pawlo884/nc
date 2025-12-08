# Fix: Wolne requesty w Django Admin (czasem >1 minuta)

## ✅ ROZWIĄZANE
**Problem był spowodowany łączeniem się bezpośrednio przez Django (port 8000) zamiast przez nginx (port 8080).**

### Rozwiązanie
**Używaj nginx jako reverse proxy:**
- ✅ **Poprawnie**: `http://localhost:8080/admin/` (przez nginx)
- ❌ **Niepoprawnie**: `http://localhost:8000/admin/` (bezpośrednio Django/Gunicorn)

### Dlaczego nginx jest lepszy?
1. **Reverse proxy** - nginx obsługuje połączenia i przekazuje do Django
2. **Timeouty** - nginx ma lepszą kontrolę nad timeoutami
3. **Buffering** - nginx może buforować odpowiedzi
4. **Statyczne pliki** - nginx serwuje pliki statyczne bez obciążania Django
5. **Connection pooling** - nginx zarządza połączeniami efektywniej

---

## Problem (zdiagnozowany)
- Requesty w przeglądarce czasem trwają minutę lub dłużej
- Testy automatyczne pokazują szybkie odpowiedzi (<1s)
- Problem występuje tylko w przeglądarce, nie w testach
- **Przyczyna**: Łączenie się bezpośrednio przez Django zamiast przez nginx

## Możliwe przyczyny

### 1. ✅ Nginx - Brak timeoutów proxy (NAPRAWIONE)
**Problem**: `nginx.conf` nie miał ustawionych timeoutów dla proxy, co mogło powodować długie oczekiwanie.

**Rozwiązanie**: Dodano timeouty do `nginx.conf`:
```nginx
proxy_connect_timeout 10s;      # Czas na połączenie z backendem
proxy_send_timeout 60s;         # Czas na wysłanie requestu
proxy_read_timeout 60s;         # Czas na odczyt odpowiedzi (1 minuta max)
proxy_buffering off;            # Wyłączone dla szybszej odpowiedzi
```

### 2. ⚠️ Debug Toolbar - Może spowalniać requesty
**Problem**: Debug Toolbar wykonuje dodatkowe zapytania SQL i zbiera statystyki, co może spowalniać requesty w przeglądarce.

**Sprawdzenie**: Debug Toolbar jest włączony w `MIDDLEWARE` i `INSTALLED_APPS`.

**Rozwiązanie opcjonalne**: Można wyłączyć Debug Toolbar dla admin:
```python
# nc/settings/dev.py
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: not request.path.startswith('/admin/'),
}
```

### 3. ⚠️ Database Connection Pooling
**Problem**: `CONN_MAX_AGE = 0` zamyka połączenia natychmiast, co może powodować wolne pierwsze połączenia po czasie idle.

**Aktualna konfiguracja**: `CONN_MAX_AGE = 0` (zamyka połączenia natychmiast)

**Rozwiązanie opcjonalne**: Dla development można zwiększyć:
```python
# nc/settings/dev.py
DATABASES['zzz_matterhorn1']['CONN_MAX_AGE'] = 60  # 60 sekund
```

### 4. ⚠️ Pierwsze połączenie po czasie idle
**Problem**: Po dłuższym czasie bezczynności pierwsze połączenie może być wolne (TCP handshake, cache miss).

**Test**: Uruchom `test_admin_idle_connection.py` aby sprawdzić czy problem występuje.

### 5. ⚠️ Sesja/Cookies w przeglądarce
**Problem**: Przeglądarka może mieć problemy z sesją lub cookies, co powoduje timeouty.

**Sprawdzenie**: Otwórz DevTools (F12) → Network → sprawdź czy requesty są w stanie "pending" lub "stalled".

## Wykonane naprawy

### ✅ 1. Nginx timeouty (nginx.conf)
Dodano timeouty proxy aby zapobiec długiemu oczekiwaniu:
- `proxy_connect_timeout 10s`
- `proxy_send_timeout 60s`
- `proxy_read_timeout 60s`
- `proxy_buffering off`

### ✅ 2. Testy diagnostyczne
Stworzono testy do diagnozowania problemu:
- `test_admin_browser_simulation.py` - symulacja przeglądarki
- `test_admin_idle_connection.py` - test połączenia po czasie idle

## Następne kroki diagnostyczne

### 1. Sprawdź logi Django
```bash
# Sprawdź logi Django podczas wolnego requestu
tail -f logs/matterhorn/*.log
```

### 2. Sprawdź logi Nginx
```bash
# Jeśli używasz Docker
docker-compose logs -f nginx
```

### 3. Sprawdź w DevTools
1. Otwórz przeglądarkę → F12 → Network
2. Kliknij filtr/link który jest wolny
3. Sprawdź:
   - Status requestu (pending/stalled?)
   - Timing (gdzie spędza czas?)
   - Headers (czy są problemy z cookies/sesją?)

### 4. Test z wyłączonym Debug Toolbar
Tymczasowo wyłącz Debug Toolbar i sprawdź czy problem znika:
```python
# nc/settings/dev.py
MIDDLEWARE = [
    # ... inne middleware ...
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',  # Wyłącz
]
```

### 5. Test bezpośrednio do Django (bez Nginx)
Sprawdź czy problem występuje gdy łączysz się bezpośrednio do Django:
```bash
# Uruchom Django bezpośrednio
python manage.py runserver 0.0.0.0:8001 --settings=nc.settings.dev

# Testuj:
http://localhost:8001/admin/matterhorn1/product/?brand__id__exact=28
```

## Zalecenia

1. **Restart Nginx** po zmianach w `nginx.conf`:
   ```bash
   docker-compose restart nginx
   ```

2. **Monitoruj logi** podczas wolnego requestu:
   ```bash
   docker-compose logs -f web nginx
   ```

3. **Sprawdź czy problem występuje tylko w przeglądarce**:
   - Testy automatyczne pokazują szybkie odpowiedzi
   - Problem może być specyficzny dla przeglądarki (cookies, sesja, cache)

4. **Sprawdź czy problem jest związany z konkretnym filtrem**:
   - Czy wszystkie filtry są wolne?
   - Czy tylko niektóre są wolne?
   - Czy problem występuje tylko przy pierwszym użyciu filtra?

## Testy

Uruchom testy diagnostyczne:
```bash
# Test symulujący przeglądarkę
python test_admin_browser_simulation.py

# Test połączenia po czasie idle (zajmie ~2 minuty)
python test_admin_idle_connection.py
```

## Status

- ✅ **ROZWIĄZANE** - Problem był spowodowany łączeniem się bezpośrednio przez Django zamiast przez nginx
- ✅ Nginx timeouty - naprawione
- ✅ Testy diagnostyczne - stworzone
- ✅ Użycie nginx (port 8080) zamiast bezpośrednio Django (port 8000)

## Ważne informacje

### Porty w docker-compose.dev.yml
- **Django/Gunicorn**: port `8000` (wewnętrzny, nie powinien być używany bezpośrednio)
- **Nginx**: port `8080` (zewnętrzny, **używaj tego portu**)

### Konfiguracja
```yaml
# docker-compose.dev.yml
web:
  ports:
    - "8000:8000"  # Tylko dla wewnętrznego dostępu

nginx:
  ports:
    - "8080:80"    # Użyj tego portu!
```

### Zalecenie
**Zawsze używaj nginx jako reverse proxy:**
- Development: `http://localhost:8080/admin/`
- Production: `http://your-domain/admin/` (przez nginx)

