# 🚀 Matterhorn1 - Inteligentny System Importu

## 📋 Przegląd

**Inteligentny system importu** z automatycznym sprawdzaniem luk w ID i planowanymi aktualizacjami:

1. **Sprawdza luki w ID** - jak w starym kodzie
2. **Importuje tylko nowe produkty** - pomija istniejące
3. **Aktualizuje INVENTORY** - tylko zmienione dane
4. **Planowane aktualizacje** - co 10 minut

## 🎯 Główne Zadania

### **1. `full_import_and_update`** - Pełny import
- Importuje wszystkie produkty od ostatniego ID
- Automatycznie aktualizuje INVENTORY
- Kontynuuje aż skończą się produkty

### **2. `scheduled_import_and_update`** - Planowane aktualizacje
- Sprawdza nowe produkty co 10 minut
- Aktualizuje INVENTORY (tylko zmienione)
- Inteligentne sprawdzanie luk w ID

## 🔍 Inteligentne Sprawdzanie Luk w ID

**Logika (jak w starym kodzie):**
```
1. Sprawdza kolejne ID od ostatniego w bazie
2. Jeśli creation_date jest NULL → zwiększa null_count
3. Jeśli null_count >= 5 → kończy sprawdzanie
4. Pomija produkty już istniejące w bazie
5. Importuje tylko nowe produkty
```

**Przykład:**
```
Baza ma produkty: 1, 2, 3, 5, 7, 10
Sprawdza: 4, 6, 8, 9, 11, 12, 13, 14, 15
Znajduje: 6, 8, 9, 11, 12
Importuje: 6, 8, 9, 11, 12
Kończy po: 13, 14, 15 (NULL creation_date)
```

## 🛠️ Użycie

### **1. Pełny Import (Pierwszy raz):**
```bash
# Import wszystkich produktów
python manage.py celery_import \
  --action full-import \
  --max-products 200000 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass" \
  --async
```

### **2. Planowane Aktualizacje (Co 10 minut):**
```bash
# Uruchom jednorazowo
python manage.py schedule_import \
  --action run-now \
  --max-products 10000 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass" \
  --async

# Zaplanuj regularne aktualizacje
python manage.py schedule_import \
  --action schedule \
  --interval-minutes 10 \
  --max-products 10000 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass" \
  --async
```

### **3. Sprawdzanie Statusu:**
```bash
# Status zadania
python manage.py schedule_import \
  --action status \
  --task-id [TASK_ID]

# Status pełnego importu
python manage.py celery_import \
  --action status \
  --task-id [TASK_ID]
```

## ⚙️ Parametry

### **Pełny Import (`celery_import`):**
- `--action full-import` - Uruchom pełny import
- `--start-id` - ID od którego rozpocząć (domyślnie ostatni w bazie)
- `--max-products` - Max produktów na iterację (domyślnie 200000)
- `--auto-continue` - Kontynuuj aż skończą się produkty (domyślnie True)
- `--async` - Uruchom asynchronicznie (zalecane)

### **Planowane Aktualizacje (`schedule_import`):**
- `--action run-now` - Uruchom jednorazowo
- `--action schedule` - Zaplanuj regularne
- `--interval-minutes` - Interwał w minutach (domyślnie 10)
- `--max-products` - Max produktów do sprawdzenia (domyślnie 10000)
- `--async` - Uruchom asynchronicznie (zalecane)

## 🔧 Uruchomienie Celery

### **Development:**
```bash
# Aktywuj środowisko wirtualne
.venv\Scripts\Activate.ps1

# Uruchom Celery worker
celery -A nc worker --loglevel=info

# Uruchom planowane aktualizacje
python manage.py schedule_import --action run-now --async
```

### **Production (Docker):**
```bash
# Uruchom wszystkie serwisy
docker-compose up celery-import celery-beat

# Uruchom planowane aktualizacje
python manage.py schedule_import --action schedule --async
```

## 📊 Monitorowanie

### **Sprawdzanie Statusu:**
```bash
# Status planowanych aktualizacji
python manage.py schedule_import --action status --task-id [TASK_ID]

# Status pełnego importu
python manage.py celery_import --action status --task-id [TASK_ID]

# Lista aktywnych zadań
celery -A nc inspect active
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

# KROK 2: Uruchom pełny import
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

### **2. Codzienne Aktualizacje (Co 10 minut):**
```bash
# Uruchom planowane aktualizacje
python manage.py schedule_import \
  --action schedule \
  --interval-minutes 10 \
  --max-products 10000 \
  --api-url "https://matterhorn.pl" \
  --username "user" \
  --password "pass" \
  --async
```

### **3. Sprawdzenie Nowych Produktów:**
```bash
# Jednorazowe sprawdzenie
python manage.py schedule_import \
  --action run-now \
  --max-products 5000 \
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
- Liczba nowych produktów/godzinę
- Liczba zaktualizowanych produktów/godzinę
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
# Co 10 minut sprawdź nowe produkty
*/10 * * * * cd /path/to/project && python manage.py schedule_import --action run-now --async

# Co godzinę pełna aktualizacja
0 * * * * cd /path/to/project && python manage.py celery_import --action full-import --async
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
- Uruchamiaj `schedule_import` co 10 minut
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
├── tasks.py                    # Główne taski Celery
│   ├── full_import_and_update  # Pełny import
│   ├── scheduled_import_and_update  # Planowane aktualizacje
│   └── get_import_status       # Sprawdzanie statusu
├── management/commands/
│   ├── celery_import.py        # Pełny import
│   ├── schedule_import.py      # Planowane aktualizacje
│   ├── import_products_bulk.py # Import po ID
│   ├── update_inventory.py     # Aktualizacja inventory
│   └── base_api_command.py     # Bazowa klasa
├── models.py                   # Modele bazy danych
└── admin.py                    # Interfejs administracyjny
```

## 🎉 Podsumowanie

**Masz teraz inteligentny system importu:**

1. **Sprawdza luki w ID** - jak w starym kodzie
2. **Importuje tylko nowe produkty** - pomija istniejące
3. **Aktualizuje INVENTORY** - tylko zmienione dane
4. **Planowane aktualizacje** - co 10 minut
5. **Automatyczne sprawdzanie** - czy są nowe produkty
6. **Inteligentne zatrzymywanie** - po 5 kolejnych NULL

**System jest gotowy do produkcji!** 🚀
