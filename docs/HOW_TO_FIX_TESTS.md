# 🔧 Jak naprawić testy - Instrukcja krok po kroku

## ✅ Co zostało naprawione

### 1. Problem z testowymi bazami danych ✅

**Błąd:** `relation "auth_user" does not exist`

**Rozwiązanie:**
- Wyłączono database routers podczas testów w `nc/settings/dev.py`
- Wszystkie bazy używają MIRROR dla testów (ta sama testowa baza)
- Naprawiono migrację `matterhorn1/migrations/0001_initial.py` - zmieniono `db_table` z `stock_history` na `matterhorn1_stock_history`

### 2. Problem z Redis podczas testów ✅

**Błąd:** `Error 11001 connecting to redis:6379`

**Rozwiązanie:**
- Wyłączono cache Redis dla testów - użyto `DummyCache`
- Wyłączono throttling dla testów (ustawiono bardzo wysokie limity)

### 3. Problem z product_id/product_uid ✅

**Błąd:** `Field name product_id is not valid for model Product`

**Rozwiązanie:**
- Dodano mapowanie `product_id = serializers.IntegerField(source='product_uid')` w `ProductSerializer`
- Zaktualizowano testy, aby używały `product_id` zamiast `product_uid` w danych API

## 📝 Zmiany w kodzie

### `nc/settings/dev.py`
```python
# Wyłącz database routers podczas testów
if 'test' in sys.argv:
    DATABASE_ROUTERS = []
    
    # Wyłącz cache/throttling dla testów
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
    
    # Wyłącz throttling dla testów
    from .base import REST_FRAMEWORK as BASE_REST_FRAMEWORK
    REST_FRAMEWORK = BASE_REST_FRAMEWORK.copy()
    REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
    REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
        'user': '1000000/day',
        'anon': '1000000/day',
        'bulk': '1000000/min',
    }
```

### `matterhorn1/serializers.py`
```python
# Mapowanie product_id (z API) na product_uid (w modelu)
product_id = serializers.IntegerField(source='product_uid')
```

### `matterhorn1/migrations/0001_initial.py`
```python
'db_table': 'matterhorn1_stock_history',  # Zmienione z 'stock_history'
```

## 🧪 Uruchamianie testów

```bash
# Wszystkie testy
python manage.py test --settings=nc.settings.dev --noinput

# Testy konkretnej aplikacji
python manage.py test matterhorn1 --settings=nc.settings.dev --noinput
python manage.py test MPD --settings=nc.settings.dev --noinput
python manage.py test web_agent --settings=nc.settings.dev --noinput

# Pojedynczy test
python manage.py test matterhorn1.tests.BrandModelTest.test_brand_creation --settings=nc.settings.dev --noinput
```

## ⚠️ Pozostałe problemy

Nadal są 10 testów z błędami (11%). Główne problemy:
- Niektóre testy API wymagają poprawy URL-i lub konfiguracji
- Testy MPD mogą wymagać dodatkowej konfiguracji
- Niektóre testy autoryzacji mogą wymagać poprawy

## 💡 Wskazówki

1. **Zawsze używaj `--noinput`** podczas uruchamiania testów w CI/CD
2. **Używaj `--keepdb`** tylko gdy jesteś pewien, że bazy są poprawne
3. **Regularnie czyść testowe bazy** jeśli pojawiają się problemy
4. **Sprawdzaj logi** jeśli testy nie działają - mogą wskazać konkretny problem

