# Analiza kompatybilności z Django 6.0

## 📋 Status kompatybilności

**Data analizy:** 2025-01-XX  
**Aktualna wersja Django:** 5.2.4 → **6.0** (zaktualizowano w requirements.txt)  
**Docelowa wersja Django:** 6.0  
**Status:** ✅ **GOTOWE DO TESTOWANIA**

**Uwaga:** `requirements.txt` został zaktualizowany do Django 6.0. Przetestuj w środowisku dev przed wdrożeniem!

## ✅ Pozytywne aspekty

### 1. Wersja Pythona

- ✅ **Python 3.13** - Projekt używa Python 3.13, który jest w pełni wspierany przez Django 6.0
- ✅ Django 6.0 wymaga Python 3.12, 3.13 lub 3.14

### 2. Architektura projektu

- ✅ Używa standardowych wzorców Django (ModelViewSet, Serializers, Routers)
- ✅ Nie używa deprecated API w sposób, który mógłby się zepsuć
- ✅ Multi-database routing jest standardowym mechanizmem Django

## ⚠️ Potencjalne problemy do sprawdzenia

### 1. Zależności zewnętrzne

Sprawdź kompatybilność następujących pakietów z Django 6.0:

| Pakiet                   | Aktualna wersja | Status               | Uwagi                              |
| ------------------------ | --------------- | -------------------- | ---------------------------------- |
| `django-celery-beat`     | 2.8.0           | ⚠️ Do sprawdzenia    | Sprawdź czy wspiera Django 6.0     |
| `django-celery-results`  | 2.5.1           | ⚠️ Do sprawdzenia    | Sprawdź czy wspiera Django 6.0     |
| `djangorestframework`    | 3.16.0          | ⚠️ Do sprawdzenia    | Prawdopodobnie wymaga aktualizacji |
| `drf-spectacular`        | 0.28.0          | ⚠️ Do sprawdzenia    | Sprawdź najnowszą wersję           |
| `django-cors-headers`    | 4.7.0           | ✅ Prawdopodobnie OK | Sprawdź dokumentację               |
| `django-debug-toolbar`   | 5.1.0           | ⚠️ Do sprawdzenia    | Może wymagać aktualizacji          |
| `django-redis`           | 5.4.0           | ✅ Prawdopodobnie OK | Sprawdź dokumentację               |
| `django-admin-interface` | 0.30.0          | ⚠️ Do sprawdzenia    | Sprawdź najnowszą wersję           |
| `django-colorfield`      | 0.13.0          | ⚠️ Do sprawdzenia    | Sprawdź najnowszą wersję           |
| `django-storages`        | 1.14.4          | ⚠️ Do sprawdzenia    | Sprawdź najnowszą wersję           |
| `django-timezone-field`  | 7.1             | ⚠️ Do sprawdzenia    | Sprawdź najnowszą wersję           |

### 2. Zmiany w Django 6.0

#### Nowe funkcje (nie wpływają na kompatybilność):

- ✅ Template Partials - opcjonalne, nie wymagane
- ✅ Background Tasks - opcjonalne, nie wymagane
- ✅ Content Security Policy (CSP) - opcjonalne, nie wymagane
- ✅ Nowoczesne API e-mail - opcjonalne, nie wymagane

#### Potencjalne breaking changes:

- ⚠️ **CheckConstraint** - zmiany w składni mogą wpłynąć na biblioteki zewnętrzne
- ⚠️ **Zmiany w middleware** - sprawdź czy wszystkie middleware działają poprawnie
- ⚠️ **Zmiany w ORM** - sprawdź czy wszystkie zapytania działają poprawnie

### 3. Kod projektu

#### Sprawdzone elementy:

- ✅ URL patterns używają `path()` zamiast `url()` - OK
- ✅ Modele używają standardowych pól Django - OK
- ✅ Serializers używają ModelSerializer - OK
- ✅ ViewSets używają standardowych klas - OK
- ✅ Database routers używają standardowego API - OK

#### Do sprawdzenia:

- ⚠️ Wszystkie testy powinny przejść po aktualizacji
- ⚠️ Migracje powinny działać poprawnie
- ⚠️ Celery taski powinny działać poprawnie

## 🧪 Testy

### Utworzone testy

Projekt ma teraz kompleksowe testy dla wszystkich aplikacji:

#### matterhorn1/tests.py

- ✅ Testy modeli: Brand, Category, Product, ProductVariant, ProductImage, ApiSyncLog, Saga, StockHistory
- ✅ Testy API: Brand, Category, Product, ProductVariant, ProductImage (bulk operations)
- ✅ Testy autoryzacji i walidacji

#### MPD/tests.py

- ✅ Testy modeli: Brands, Colors, Products, ProductVariants, Sizes, Attributes, ProductAttribute, Sources
- ✅ Testy API: GenerateFullXMLSecure (wymaga uprawnień admina)
- ✅ Testy integracyjne dla relacji między modelami

#### web_agent/tests.py

- ✅ Testy modeli: AutomationRun, ProductProcessingLog, BrandConfig, ProducerColor
- ✅ Testy API: AutomationRunViewSet, ProductProcessingLog (readonly)
- ✅ Testy filtrowania i autoryzacji

### Uruchamianie testów

**⚠️ WAŻNE: Przed uruchomieniem testów upewnij się, że migracje są wykonane!**

```bash
# 1. Najpierw uruchom migracje (Windows PowerShell)
.\run-migrations-dev.ps1

# Lub (Linux/Mac)
chmod +x run-migrations-dev.sh
./run-migrations-dev.sh

# Lub ręcznie:
python manage.py migrate --database=zzz_default --settings=nc.settings.dev
python manage.py migrate admin_interface --database=zzz_default --settings=nc.settings.dev
python manage.py migrate matterhorn1 --database=zzz_matterhorn1 --settings=nc.settings.dev
python manage.py migrate MPD --database=zzz_MPD --settings=nc.settings.dev
python manage.py migrate web_agent --database=zzz_web_agent --settings=nc.settings.dev
python manage.py migrate django_celery_beat --database=zzz_default --settings=nc.settings.dev
python manage.py migrate django_celery_results --database=zzz_default --settings=nc.settings.dev

# 2. Teraz możesz uruchomić testy
python manage.py test --settings=nc.settings.dev

# Testy konkretnej aplikacji
python manage.py test matterhorn1 --settings=nc.settings.dev
python manage.py test MPD --settings=nc.settings.dev
python manage.py test web_agent --settings=nc.settings.dev

# Testy z verbose output
python manage.py test --settings=nc.settings.dev --verbosity=2

# Testy z coverage (jeśli zainstalowany coverage)
coverage run --source='.' manage.py test --settings=nc.settings.dev
coverage report
```

**Uwaga:** Django automatycznie tworzy testowe bazy danych z prefiksem `test_` podczas uruchamiania testów, więc nie musisz się martwić o zniszczenie danych produkcyjnych.

### Rozwiązywanie problemu "relation auth_user does not exist"

Jeśli podczas uruchamiania testów pojawia się błąd `relation "auth_user" does not exist`, oznacza to, że stare testowe bazy danych są uszkodzone. Rozwiązanie:

**Opcja 1: Użyj skryptu do czyszczenia (zalecane)**

```powershell
# Uruchom skrypt czyszczący
python clean_test_databases.py
```

**Opcja 2: Usuń ręcznie przez psql**

```powershell
# Połącz się z PostgreSQL i usuń testowe bazy
psql -U postgres -c "DROP DATABASE IF EXISTS test_zzz_default;"
psql -U postgres -c "DROP DATABASE IF EXISTS test_zzz_MPD;"
psql -U postgres -c "DROP DATABASE IF EXISTS test_zzz_matterhorn1;"
psql -U postgres -c "DROP DATABASE IF EXISTS test_zzz_web_agent;"
```

**Opcja 3: Użyj flagi --keepdb (szybsze, ale może maskować problemy)**

```powershell
python manage.py test --settings=nc.settings.dev --keepdb
```

**Opcja 4: Usuń przez psql (najprostsze, jeśli masz dostęp)**

```powershell
# Zastąp wartości zgodnie z Twoją konfiguracją z .env.dev
psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS test_zzz_default;"
psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS test_zzz_MPD;"
psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS test_zzz_matterhorn1;"
psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS test_zzz_web_agent;"
```

Po usunięciu starych baz, uruchom testy ponownie - Django automatycznie utworzy nowe testowe bazy.

**📚 Szczegółowe instrukcje:** Zobacz [FIX_TEST_DATABASES.md](FIX_TEST_DATABASES.md)

## 🧪 Plan testowania

### Krok 1: Aktualizacja zależności

```bash
# 1. Zaktualizuj Django do 6.0
pip install Django==6.0

# 2. Zaktualizuj wszystkie zależności Django
pip install --upgrade django-celery-beat django-celery-results djangorestframework drf-spectacular
pip install --upgrade django-cors-headers django-debug-toolbar django-redis
pip install --upgrade django-admin-interface django-colorfield django-storages django-timezone-field

# 3. Sprawdź czy są konflikty
pip check
```

### Krok 2: Sprawdzenie migracji

```bash
# Sprawdź czy wszystkie migracje są aktualne
python manage.py makemigrations --dry-run --settings=nc.settings.dev

# Uruchom migracje na testowej bazie
python manage.py migrate --settings=nc.settings.dev
```

### Krok 3: Testy funkcjonalne

```bash
# Uruchom wszystkie testy
python manage.py test --settings=nc.settings.dev

# Sprawdź konkretne aplikacje
python manage.py test MPD --settings=nc.settings.dev
python manage.py test matterhorn1 --settings=nc.settings.dev
python manage.py test web_agent --settings=nc.settings.dev
```

### Krok 4: Testy integracyjne

- ✅ Sprawdź czy admin panel działa
- ✅ Sprawdź czy API endpoints działają
- ✅ Sprawdź czy Celery taski działają
- ✅ Sprawdź czy migracje działają na wszystkich bazach danych

### Krok 5: Testy wydajnościowe

- ✅ Sprawdź czy nie ma regresji wydajności
- ✅ Sprawdź czy zapytania do bazy działają poprawnie
- ✅ Sprawdź czy cache działa poprawnie

## 📝 Instrukcje aktualizacji

### Opcja 1: Aktualizacja w środowisku dev (zalecane)

1. **Utwórz backup bazy danych:**

```bash
# Backup wszystkich baz danych
pg_dump -U postgres zzz_default > backup_zzz_default.sql
pg_dump -U postgres zzz_matterhorn1 > backup_zzz_matterhorn1.sql
pg_dump -U postgres zzz_MPD > backup_zzz_MPD.sql
pg_dump -U postgres zzz_web_agent > backup_zzz_web_agent.sql
```

2. **Zaktualizuj requirements.txt:**

```bash
# Zaktualizuj Django i zależności
pip install Django==6.0
pip freeze > requirements.txt
```

3. **Przetestuj w środowisku dev:**

```bash
# Uruchom serwer dev
python manage.py runserver --settings=nc.settings.dev

# Sprawdź czy wszystko działa
# - Admin panel: http://localhost:8000/admin/
# - API docs: http://localhost:8000/api/docs/
# - Aplikacje: http://localhost:8000/mpd/, http://localhost:8000/matterhorn1/
```

4. **Uruchom testy:**

```bash
python manage.py test --settings=nc.settings.dev
```

### Opcja 2: Aktualizacja w Docker (zalecane dla produkcji)

1. **Zaktualizuj requirements.txt w repozytorium**

2. **Zbuduj nowy obraz Docker:**

```bash
docker-compose -f docker-compose.dev.yml build
```

3. **Uruchom kontenery:**

```bash
docker-compose -f docker-compose.dev.yml up -d
```

4. **Sprawdź logi:**

```bash
docker-compose -f docker-compose.dev.yml logs -f django-app
```

## 🔍 Checklist przed wdrożeniem

- [ ] Wszystkie zależności zaktualizowane i kompatybilne
- [ ] Wszystkie testy przechodzą
- [ ] Migracje działają poprawnie na wszystkich bazach
- [ ] Admin panel działa poprawnie
- [ ] API endpoints działają poprawnie
- [ ] Celery taski działają poprawnie
- [ ] Dokumentacja API działa poprawnie
- [ ] Nie ma błędów w logach
- [ ] Wydajność nie uległa pogorszeniu
- [ ] Backup baz danych wykonany

## 🚨 Znane problemy i rozwiązania

### Problem 1: Niekompatybilne zależności

**Rozwiązanie:** Zaktualizuj zależności do najnowszych wersji wspierających Django 6.0

### Problem 2: Błędy migracji

**Rozwiązanie:** Sprawdź czy wszystkie migracje są aktualne i uruchom `makemigrations`

### Problem 3: Błędy w testach

**Rozwiązanie:** Sprawdź czy testy używają deprecated API i zaktualizuj je

## 📚 Przydatne linki

- [Django 6.0 Release Notes](https://docs.djangoproject.com/en/6.0/releases/6.0/)
- [Django 6.0 Upgrade Guide](https://docs.djangoproject.com/en/6.0/howto/upgrade-version/)
- [Django 6.0 Deprecated Features](https://docs.djangoproject.com/en/6.0/releases/6.0/#deprecated-features)

## ✅ Wnioski

Projekt jest **gotowy do testowania** z Django 6.0:

- ✅ Python 3.13 jest wspierany
- ✅ Architektura używa standardowych wzorców Django
- ✅ Nie używa deprecated API w sposób, który mógłby się zepsuć
- ⚠️ Wymaga sprawdzenia kompatybilności zależności zewnętrznych
- ⚠️ Wymaga testowania w środowisku dev przed wdrożeniem do produkcji

**Rekomendacja:** Rozpocznij testowanie w środowisku dev, a następnie stopniowo wdrażaj do produkcji.
