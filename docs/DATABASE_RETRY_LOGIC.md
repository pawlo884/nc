# Database Retry Logic

## Opis

Custom database backend z automatycznym ponawianiem połączeń z bazami danych PostgreSQL. Rozwiązuje problemy z timeoutami i błędami sieciowymi poprzez automatyczne retry połączeń.

## Konfiguracja

### Ustawienia w `nc/settings/base.py`

```python
DATABASE_RETRY_CONFIG = {
    'max_retries': 3,              # Maksymalna liczba prób połączenia (domyślnie: 3)
    'retry_delay': 2,              # Bazowe opóźnienie między próbami w sekundach (domyślnie: 2s)
    'retry_backoff': True,         # Exponential backoff (2^attempt * delay) (domyślnie: True)
    'retry_max_delay': 30,         # Maksymalne opóźnienie między próbami w sekundach (domyślnie: 30s)
}
```

### Backend w konfiguracji baz danych

Wszystkie bazy danych używają custom backendu:

```python
DATABASES = {
    'default': {
        'ENGINE': 'nc.db_backend.base',  # Custom backend z retry logic
        # ... pozostałe ustawienia
    },
    # ... inne bazy
}
```

## Jak działa

### Automatyczne ponawianie połączeń

1. **Przy tworzeniu nowego połączenia** (`get_new_connection`):
   - Próba połączenia z bazą danych
   - W przypadku błędu timeout/network:
     - Logowanie błędu
     - Obliczenie opóźnienia (exponential backoff)
     - Czekanie przed następną próbą
     - Powtórzenie do `max_retries` razy

2. **Przy sprawdzaniu istniejącego połączenia** (`ensure_connection`):
   - Sprawdzenie czy połączenie jest aktywne
   - W przypadku nieaktywnego połączenia:
     - Zamknięcie starego połączenia
     - Próba ponownego połączenia z retry logic

### Typy błędów, które są ponawiane

Retry logic działa dla następujących błędów:

- `OperationalError` (Django)
- `InterfaceError` (Django)
- `Psycopg2OperationalError` (psycopg2)

Błędy są ponawiane tylko jeśli zawierają w komunikacie jedno z następujących słów kluczowych:
- `timeout`, `timed out`
- `connection`
- `network`
- `refused`
- `unreachable`
- `broken pipe`
- `closed`
- `lost connection`
- `server closed`

### Exponential Backoff

Gdy `retry_backoff=True` (domyślnie), opóźnienie między próbami rośnie wykładniczo:

- Próba 1: `delay * 2^0 = delay` (np. 2s)
- Próba 2: `delay * 2^1 = delay * 2` (np. 4s)
- Próba 3: `delay * 2^2 = delay * 4` (np. 8s)
- Próba 4: `delay * 2^3 = delay * 8` (np. 16s)

Opóźnienie nie przekroczy wartości `retry_max_delay` (domyślnie 30s).

## Logowanie

Retry logic loguje wszystkie operacje na poziomie:

- **DEBUG**: Informacje o każdej próbie połączenia
- **INFO**: Sukces po retry (gdy potrzeba było więcej niż 1 próba)
- **WARNING**: Błędy połączenia i informacje o retry
- **ERROR**: Wyczerpanie wszystkich prób lub błędy nie-retryable

Przykładowe logi:

```
[DB Retry] Próba połączenia 1/4 do bazy matterhorn1 (host: 212.127.93.27)
[DB Retry] ⏳ Błąd połączenia z bazą matterhorn1 (próba 1/4): timeout expired. Ponowienie za 2.0s...
[DB Retry] ✓ Połączenie z bazą matterhorn1 udane po 2 próbach
```

## Przykład użycia

Retry logic działa automatycznie dla wszystkich operacji na bazie danych:

```python
from django.db import connection

# Automatyczne retry przy połączeniu
connection.ensure_connection()

# Automatyczne retry przy query
from matterhorn1.models import Product
products = Product.objects.all()  # Automatyczne retry jeśli potrzeba
```

## Testowanie

Użyj skryptu diagnostycznego do testowania połączeń:

```bash
python scripts/check_db_connections.py
```

Skrypt sprawdza:
1. Podstawowe połączenie psycopg2
2. Połączenie przez Django ORM (z retry logic)

## Rozwiązywanie problemów

### Problem: Wszystkie próby kończą się niepowodzeniem

**Rozwiązanie:**
1. Sprawdź dostępność serwera PostgreSQL: `telnet <host> <port>`
2. Sprawdź firewall i sieć
3. Zwiększ `connect_timeout` w `OPTIONS` konfiguracji bazy
4. Zwiększ `max_retries` w `DATABASE_RETRY_CONFIG`

### Problem: Retry działa, ale zajmuje dużo czasu

**Rozwiązanie:**
1. Zmniejsz `retry_delay` jeśli masz szybką sieć
2. Wyłącz `retry_backoff` jeśli chcesz stałe opóźnienia
3. Zmniejsz `retry_max_delay` dla szybszego wykrywania problemów

### Problem: Retry nie działa dla niektórych błędów

**Rozwiązanie:**
1. Sprawdź czy błąd jest w liście `RETRYABLE_ERRORS`
2. Sprawdź czy komunikat błędu zawiera słowa kluczowe z `RETRYABLE_ERROR_KEYWORDS`
3. Błędy nie-retryable są rzucane natychmiast (np. błędy autoryzacji)

## Pliki

- `nc/db_backend/base.py` - Custom database backend z retry logic
- `nc/db_backend/__init__.py` - Inicjalizacja pakietu
- `nc/settings/base.py` - Konfiguracja retry (`DATABASE_RETRY_CONFIG`)
- `scripts/check_db_connections.py` - Skrypt diagnostyczny

## Zgodność

Retry logic jest w pełni zgodny z Django ORM i działa transparentnie dla wszystkich operacji na bazie danych. Nie wymaga zmian w istniejącym kodzie.

