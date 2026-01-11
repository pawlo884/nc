# Web Agent - Moduł automatyzacji przeglądarki

Moduł automatyzacji do wypełniania formularzy MPD za pomocą Selenium i AI.

## Wymagane zmienne środowiskowe

Dodaj do pliku `.env.dev`:

```env
# Web Agent - Automatyzacja przeglądarki
DJANGO_ADMIN_USERNAME=admin
DJANGO_ADMIN_PASSWORD=twoje_haslo_admin
WEB_AGENT_BASE_URL=http://localhost:8000
OPENAI_API_KEY=twoj_klucz_openai
BROWSER_HEADLESS=False  # Opcjonalne, domyślnie False (przeglądarka widoczna)
```

## Uruchomienie automatyzacji

### Przez API

```bash
curl -X POST http://localhost:8000/api/web-agent/automation-runs/start-automation/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN" \
  -d '{
    "brand_id": 28,
    "category_id": 15,
    "filters": {
      "active": true,
      "is_mapped": false
    }
  }'
```

### Przez Django shell

```python
from web_agent.tasks import automate_mpd_form_filling

# Uruchom task w tle
task = automate_mpd_form_filling.delay(
    brand_id=28,
    category_id=15,
    filters={'active': True, 'is_mapped': False}
)

# Sprawdź status
print(task.id)
print(task.status)
```

## Monitorowanie

1. **Admin Django**: http://localhost:8000/admin/web_agent/
   - `AutomationRun` - lista uruchomień automatyzacji
   - `ProductProcessingLog` - logi przetwarzania produktów

2. **API Endpointy**:
   - `GET /api/web-agent/automation-runs/` - lista uruchomień
   - `GET /api/web-agent/automation-runs/{id}/` - szczegóły uruchomienia
   - `GET /api/web-agent/automation-runs/{id}/logs/` - logi produktów
   - `POST /api/web-agent/automation-runs/start-automation/` - uruchom automatyzację

3. **Flower** (monitoring Celery): http://localhost:5555

## Jak działa

1. Task Celery uruchamia przeglądarkę Chrome
2. Loguje się do admin Django
3. Przechodzi do listy produktów z filtrami (marka, kategoria, active, is_mapped)
4. Pobiera listę produktów do przetworzenia
5. Dla każdego produktu:
   - Pobiera dane z bazy `matterhorn1`
   - Modyfikuje dane przez OpenAI (nazwa, opis, krótki opis)
   - Przechodzi do strony change form produktu
   - Wypełnia formularz MPD
   - Klika przycisk "Utwórz nowy produkt w MPD"
   - Czeka na wynik i loguje go

## Struktura

```
web_agent/
├── automation/
│   ├── ai_processor.py          # Modyfikacja danych przez OpenAI
│   ├── browser_automation.py    # Automatyzacja Selenium
│   └── product_processor.py     # Logika przetwarzania produktów
├── models.py                    # AutomationRun, ProductProcessingLog
├── tasks.py                     # Task Celery
├── views.py                     # API ViewSets
├── serializers.py               # Serializery DRF
├── urls.py                      # Routing URL
└── admin.py                     # Admin Django
```

## Troubleshooting

### Błąd: "ChromeDriver not found"
```bash
# ChromeDriver jest instalowany automatycznie przez webdriver-manager
# Jeśli wystąpi błąd, spróbuj zaktualizować:
pip install --upgrade webdriver-manager
```

### Błąd: "DJANGO_ADMIN_PASSWORD nie jest ustawione"
```bash
# Upewnij się, że masz zmienne w .env.dev:
echo "DJANGO_ADMIN_PASSWORD=twoje_haslo" >> .env.dev
```

### Błąd: "OpenAI API key is required"
```bash
# Dodaj klucz API OpenAI do .env.dev:
echo "OPENAI_API_KEY=sk-..." >> .env.dev
```

### Przeglądarka nie zamyka się
```bash
# Ustaw headless mode:
echo "BROWSER_HEADLESS=True" >> .env.dev
```

## Przykładowe użycie

### Automatyzacja dla marki Lupo Line

```python
from web_agent.tasks import automate_mpd_form_filling

# Produkty marki Lupo Line (ID 28), kategoria stroje kąpielowe (ID 15)
task = automate_mpd_form_filling.delay(
    brand_id=28,
    category_id=15,
    filters={
        'active': True,      # Tylko aktywne produkty
        'is_mapped': False   # Tylko niezmapowane produkty
    }
)

print(f"Task uruchomiony: {task.id}")
```

### Sprawdzanie statusu

```python
from web_agent.models import AutomationRun

# Ostatnie uruchomienie
run = AutomationRun.objects.last()
print(f"Status: {run.status}")
print(f"Przetworzono: {run.products_processed}")
print(f"Sukcesy: {run.products_success}")
print(f"Błędy: {run.products_failed}")

# Logi produktów
for log in run.product_logs.all():
    print(f"Produkt {log.product_id}: {log.status}")
    if log.mpd_product_id:
        print(f"  MPD ID: {log.mpd_product_id}")
    if log.error_message:
        print(f"  Błąd: {log.error_message}")
```

