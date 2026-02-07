# 🚀 Matterhorn1 Celery Tasks - Dokumentacja

## 📋 Przegląd

System Celery tasks dla automatycznego importu produktów z API ITEMS i aktualizacji stanów magazynowych z API INVENTORY.

## 🎯 Główne Zadania

### 1. **Import Produktów z ITEMS** (`import_products_from_items`)
- Pobiera produkty z API `/B2BAPI/ITEMS/`
- Rozpoczyna od ostatniego ID w bazie danych
- Importuje produkty w zakresie ID
- Obsługuje retry w przypadku błędów

### 2. **Aktualizacja Inventory** (`update_inventory_from_api`)
- Pobiera dane z API `/B2BAPI/ITEMS/INVENTORY/`
- Aktualizuje tylko dane zmienione od `last_update`
- Aktualizuje ceny i stany magazynowe
- Automatycznie wykrywa ostatnią aktualizację

### 3. **Sekwencyjny Import** (`import_products_sequence`)
- Najpierw importuje produkty z ITEMS
- Następnie aktualizuje inventory
- Zapewnia poprawną kolejność operacji

## 🛠️ Użycie

### **Komenda Zarządzająca:**
```bash
python manage.py celery_import --action [AKCJA] [OPCJE]
```

### **Dostępne Akcje:**

#### **1. Import Produktów (ITEMS)**
```bash
# Import synchroniczny (10 produktów)
python manage.py celery_import \
  --action import \
  --max-products 10 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass"

# Import asynchroniczny (1000 produktów)
python manage.py celery_import \
  --action import \
  --max-products 1000 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass" \
  --async

# Import od konkretnego ID
python manage.py celery_import \
  --action import \
  --start-id 5000 \
  --end-id 6000 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass"
```

#### **2. Aktualizacja Inventory**
```bash
# Aktualizacja od ostatniej daty
python manage.py celery_import \
  --action update \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass"

# Aktualizacja od konkretnej daty
python manage.py celery_import \
  --action update \
  --last-update "2025-01-15 10:00:00" \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass"

# Aktualizacja asynchroniczna
python manage.py celery_import \
  --action update \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass" \
  --async
```

#### **3. Sekwencyjny Import**
```bash
# Pełny sekwencyjny import
python manage.py celery_import \
  --action sequence \
  --max-products 10000 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass"

# Sekwencyjny import bez inventory
python manage.py celery_import \
  --action sequence \
  --max-products 5000 \
  --skip-inventory \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass"

# Sekwencyjny import asynchroniczny
python manage.py celery_import \
  --action sequence \
  --max-products 20000 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass" \
  --async
```

#### **4. Import w Batchach**
```bash
# Import w batchach (dla dużych importów)
python manage.py celery_import \
  --action batch \
  --batch-ranges "1-1000,1001-2000,2001-3000" \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass"
```

#### **5. Planowanie Aktualizacji**
```bash
# Planowanie aktualizacji co 30 minut
python manage.py celery_import \
  --action schedule \
  --interval-minutes 30 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass"
```

#### **6. Sprawdzanie Statusu**
```bash
# Sprawdź status zadania
python manage.py celery_import \
  --action status \
  --task-id "abc123-def456-ghi789"
```

## 🔧 Konfiguracja

### **Ustawienia w Django:**
```python
# settings.py
MATTERHORN_API_URL = 'https://matterhorn.pl'
MATTERHORN_API_USERNAME = 'your_username'
MATTERHORN_API_PASSWORD = 'your_password'
```

### **Uruchomienie Celery Worker:**
```bash
# Development
celery -A nc worker --loglevel=info

# Production (z Docker)
docker-compose up celery-import
```

### **Uruchomienie Celery Beat (planowanie):**
```bash
# Development
celery -A nc beat --loglevel=info

# Production (z Docker)
docker-compose up celery-beat
```

## 📊 Monitorowanie

### **Flower (Web UI):**
```bash
# Uruchomienie Flower
celery -A nc flower

# Dostęp: http://localhost:5555
```

### **Sprawdzanie Statusu:**
```bash
# Lista aktywnych zadań
celery -A nc inspect active

# Lista zarejestrowanych zadań
celery -A nc inspect registered

# Statystyki workerów
celery -A nc inspect stats
```

## 🚀 Przykłady Użycia

### **1. Pierwszy Import (200,000 produktów):**
```bash
# KROK 1: Import podstawowych danych
python manage.py celery_import \
  --action sequence \
  --max-products 200000 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass" \
  --async

# Sprawdź status
python manage.py celery_import \
  --action status \
  --task-id [TASK_ID]
```

### **2. Codzienna Aktualizacja:**
```bash
# Aktualizacja inventory co godzinę
python manage.py celery_import \
  --action schedule \
  --interval-minutes 60 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass"
```

### **3. Import Nowych Produktów:**
```bash
# Import tylko nowych produktów (od ostatniego ID)
python manage.py celery_import \
  --action import \
  --max-products 1000 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass" \
  --async
```

### **4. Import w Batchach (dla bardzo dużych importów):**
```bash
# Podziel import na batchy
python manage.py celery_import \
  --action batch \
  --batch-ranges "1-10000,10001-20000,20001-30000,30001-40000,40001-50000" \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass"
```

## ⚙️ Parametry

### **Wspólne Parametry:**
- `--api-url`: URL API Matterhorn
- `--username`: Nazwa użytkownika API
- `--password`: Hasło API
- `--batch-size`: Rozmiar batcha (domyślnie 100)
- `--dry-run`: Tryb testowy
- `--verbose`: Szczegółowe logowanie
- `--async`: Uruchom asynchronicznie

### **Parametry Importu:**
- `--start-id`: ID produktu od którego rozpocząć
- `--end-id`: ID produktu na którym zakończyć
- `--max-products`: Maksymalna liczba produktów

### **Parametry Aktualizacji:**
- `--last-update`: Data ostatniej aktualizacji
- `--interval-minutes`: Interwał w minutach

### **Parametry Batch:**
- `--batch-ranges`: Zakresy batchów (format: "1-1000,1001-2000")

## 🔍 Logi i Debugowanie

### **Logi Celery:**
```bash
# Logi workerów
tail -f /var/log/celery/worker.log

# Logi beat
tail -f /var/log/celery/beat.log
```

### **Logi Django:**
```bash
# Logi aplikacji
tail -f /var/log/django/matterhorn1.log
```

### **Sprawdzanie Błędów:**
```bash
# Lista błędów w Celery
celery -A nc inspect failed

# Szczegóły błędu
celery -A nc inspect active_queues
```

## 🎯 Najlepsze Praktyki

### **1. Duże Importy:**
- Używaj `--async` dla importów > 1000 produktów
- Podziel na batchy dla importów > 50,000 produktów
- Monitoruj zużycie pamięci

### **2. Regularne Aktualizacje:**
- Używaj `schedule` dla automatycznych aktualizacji
- Ustaw `interval-minutes` na 30-60 minut
- Monitoruj logi pod kątem błędów

### **3. Bezpieczeństwo:**
- Używaj zmiennych środowiskowych dla danych API
- Nie loguj haseł w logach
- Używaj `--dry-run` do testowania

### **4. Wydajność:**
- Dostosuj `--batch-size` do wydajności API
- Używaj retry dla niestabilnych połączeń
- Monitoruj limity API (2 requesty/sekundę)

## 🚨 Rozwiązywanie Problemów

### **Błąd 403 Forbidden:**
- Sprawdź dane uwierzytelniające API
- Sprawdź czy API jest dostępne
- Sprawdź limity API

### **Błąd Timeout:**
- Zwiększ timeout w ustawieniach Celery
- Zmniejsz `--batch-size`
- Sprawdź wydajność sieci

### **Błąd Memory:**
- Zmniejsz `--max-products`
- Użyj importu w batchach
- Zwiększ pamięć workerów

### **Błąd Database:**
- Sprawdź połączenie z bazą danych
- Sprawdź czy tabele istnieją
- Sprawdź uprawnienia bazy danych

## 📈 Metryki i Monitoring

### **Kluczowe Metryki:**
- Liczba importowanych produktów/godzinę
- Czas wykonania zadań
- Wskaźnik błędów
- Zużycie pamięci workerów

### **Alerty:**
- Błędy importu > 5%
- Czas wykonania > 2 godziny
- Brak nowych danych > 24 godziny
- Zużycie pamięci > 80%

## 🔄 Automatyzacja

### **Cron Jobs:**
```bash
# Codzienna aktualizacja o 2:00
0 2 * * * cd /path/to/project && python manage.py celery_import --action update

# Co godzinę aktualizacja inventory
0 * * * * cd /path/to/project && python manage.py celery_import --action update
```

### **Docker Compose:**
```yaml
# docker-compose.yml
services:
  celery-import:
    build: .
    command: celery -A nc worker -Q import_queue --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
```

## 📚 Dodatkowe Zasoby

- [Dokumentacja Celery](https://docs.celeryproject.org/)
- [Django Celery Beat](https://django-celery-beat.readthedocs.io/)
- [Flower Monitoring](https://flower.readthedocs.io/)
- [Redis Configuration](https://redis.io/documentation)

---

**✅ System Celery Tasks jest gotowy do użycia!** 🚀
