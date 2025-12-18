# 🚀 Matterhorn1 - Prosty System Celery

## 📋 Przegląd

**Jeden główny task** do pełnego importu i aktualizacji:
1. **Import produktów z ITEMS** (od ostatniego ID)
2. **Automatyczna aktualizacja INVENTORY** (po każdym imporcie)
3. **Auto-continue** - kontynuuje aż skończą się produkty

## 🎯 Główny Task

### **`full_import_and_update`** - Jeden task do wszystkiego

**Logika działania:**
```
ITERACJA 1:
├── Import produktów z ITEMS (ID 1-200000)
├── Aktualizacja INVENTORY (tylko zmienione)
└── Sprawdź czy są nowe produkty

ITERACJA 2:
├── Import produktów z ITEMS (ID 200001-400000)
├── Aktualizacja INVENTORY (tylko zmienione)
└── Sprawdź czy są nowe produkty

... kontynuuje aż skończą się produkty
```

## 🛠️ Użycie

### **Komenda:**
```bash
python manage.py celery_import --action full-import [OPCJE]
```

### **Przykłady:**

#### **1. Pierwszy import (200,000 produktów):**
```bash
# Uruchom asynchronicznie (zalecane)
python manage.py celery_import \
  --action full-import \
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

#### **2. Import od konkretnego ID:**
```bash
python manage.py celery_import \
  --action full-import \
  --start-id 50000 \
  --max-products 100000 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass" \
  --async
```

#### **3. Import synchroniczny (test):**
```bash
python manage.py celery_import \
  --action full-import \
  --max-products 1000 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass" \
  --dry-run
```

#### **4. Import bez auto-continue (tylko jedna iteracja):**
```bash
python manage.py celery_import \
  --action full-import \
  --max-products 50000 \
  --no-auto-continue \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass" \
  --async
```

## ⚙️ Parametry

### **Wymagane:**
- `--action full-import` - Uruchom pełny import
- `--api-url` - URL API Matterhorn
- `--username` - Nazwa użytkownika API
- `--password` - Hasło API

### **Opcjonalne:**
- `--start-id` - ID produktu od którego rozpocząć (domyślnie ostatni w bazie)
- `--max-products` - Max produktów na iterację (domyślnie 200000)
- `--auto-continue` - Kontynuuj aż skończą się produkty (domyślnie True)
- `--async` - Uruchom asynchronicznie (zalecane)
- `--dry-run` - Tryb testowy
- `--verbose` - Szczegółowe logowanie

## 🔧 Uruchomienie Celery

### **Development:**
```bash
# Aktywuj środowisko wirtualne
.venv\Scripts\Activate.ps1

# Uruchom Celery worker
celery -A nc worker --loglevel=info

# W drugim terminalu uruchom import
python manage.py celery_import --action full-import --async
```

### **Production (Docker):**
```bash
# Uruchom wszystkie serwisy
docker-compose up celery-import celery-beat

# Uruchom import
python manage.py celery_import --action full-import --async
```

## 📊 Monitorowanie

### **Sprawdzanie Statusu:**
```bash
# Status konkretnego zadania
python manage.py celery_import --action status --task-id [TASK_ID]

# Lista aktywnych zadań
celery -A nc inspect active

# Statystyki workerów
celery -A nc inspect stats
```

### **Flower (Web UI):**
```bash
# Uruchomienie Flower
celery -A nc flower

# Dostęp: http://localhost:5555
```

## 🎯 Przykłady Użycia

### **1. Pierwszy Import 200,000 Produktów:**
```bash
# KROK 1: Uruchom Celery worker
celery -A nc worker --loglevel=info

# KROK 2: Uruchom import asynchronicznie
python manage.py celery_import \
  --action full-import \
  --max-products 200000 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass" \
  --async

# KROK 3: Sprawdź status
python manage.py celery_import \
  --action status \
  --task-id [TASK_ID]
```

### **2. Codzienna Aktualizacja:**
```bash
# Uruchom import (automatycznie zaktualizuje INVENTORY)
python manage.py celery_import \
  --action full-import \
  --max-products 10000 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass" \
  --async
```

### **3. Import Nowych Produktów:**
```bash
# Import tylko nowych produktów (od ostatniego ID)
python manage.py celery_import \
  --action full-import \
  --max-products 50000 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass" \
  --async
```

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

## 🚨 Rozwiązywanie Problemów

### **Błąd 403 Forbidden:**
- Sprawdź dane uwierzytelniające API
- Sprawdź czy API jest dostępne
- Sprawdź limity API

### **Błąd Timeout:**
- Zwiększ timeout w ustawieniach Celery
- Zmniejsz `--max-products`
- Sprawdź wydajność sieci

### **Błąd Memory:**
- Zmniejsz `--max-products`
- Zwiększ pamięć workerów
- Użyj importu w mniejszych batchach

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
0 2 * * * cd /path/to/project && python manage.py celery_import --action full-import --async

# Co 6 godzin aktualizacja
0 */6 * * * cd /path/to/project && python manage.py celery_import --action full-import --async
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

## 🎯 Najlepsze Praktyki

### **1. Duże Importy:**
- Używaj `--async` dla importów > 1000 produktów
- Ustaw `--max-products` na 200000 dla optymalnej wydajności
- Monitoruj zużycie pamięci

### **2. Regularne Aktualizacje:**
- Uruchamiaj import co 6-12 godzin
- Używaj `--async` dla automatycznych aktualizacji
- Monitoruj logi pod kątem błędów

### **3. Bezpieczeństwo:**
- Używaj zmiennych środowiskowych dla danych API
- Nie loguj haseł w logach
- Używaj `--dry-run` do testowania

### **4. Wydajność:**
- Dostosuj `--max-products` do wydajności API
- Używaj retry dla niestabilnych połączeń
- Monitoruj limity API (2 requesty/sekundę)

## 📚 Struktura Systemu

```
matterhorn1/
├── tasks.py                    # Główny task full_import_and_update
├── management/commands/
│   ├── celery_import.py        # Komenda zarządzająca
│   ├── import_products_bulk.py # Import po ID
│   ├── update_inventory.py     # Aktualizacja inventory
│   └── base_api_command.py     # Bazowa klasa
├── models.py                   # Modele bazy danych
└── admin.py                    # Interfejs administracyjny
```

## 🎉 Podsumowanie

**Masz teraz prosty system z jednym głównym taskiem:**

1. **`full_import_and_update`** - robi wszystko automatycznie
2. **Import ITEMS** - od ostatniego ID
3. **Aktualizacja INVENTORY** - po każdym imporcie
4. **Auto-continue** - kontynuuje aż skończą się produkty
5. **Proste komendy** - jedna komenda do wszystkiego

**System jest gotowy do produkcji!** 🚀
