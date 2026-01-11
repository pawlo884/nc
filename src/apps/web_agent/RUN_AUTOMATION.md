# Jak uruchomić automatyzację

## Sposób 1: Przez skrypt (ZALECANE)

### Podstawowe użycie:
```bash
# Aktywuj środowisko wirtualne
source .venv/Scripts/activate  # Linux/Mac
# lub
.\.venv\Scripts\Activate.ps1   # Windows PowerShell

# Uruchom automatyzację
python run_automation.py --brand "Axami"
```

### Z kategorią:
```bash
python run_automation.py --brand "Axami" --category "Biustonosze"
```

### Z limitem produktów:
```bash
python run_automation.py --brand "DKaren" --max 10
```

### Wszystkie opcje:
```bash
python run_automation.py --brand "Axami" --category "Biustonosze" --max 20
```

### Pomoc:
```bash
python run_automation.py --help
```

## Sposób 2: Przez Django shell

```python
from web_agent.tasks import automate_mpd_form_filling

# Uruchom task Celery
task = automate_mpd_form_filling.delay(
    brand_name='Axami',
    category_name='Biustonosze',
    filters={
        'active': True,
        'is_mapped': False,
        'max_products': 10
    }
)

print(f"Task ID: {task.id}")
```

## Sposób 3: Przez API

```bash
curl -X POST http://localhost:8000/api/web-agent/automation-runs/start-automation/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN" \
  -d '{
    "brand_name": "Axami",
    "category_name": "Biustonosze",
    "filters": {
      "active": true,
      "is_mapped": false,
      "max_products": 10
    }
  }'
```

## Parametry

- `--brand`, `-b`: **WYMAGANE** - Nazwa marki (np. "Axami", "DKaren", "Lupo Line")
- `--category`, `-c`: Opcjonalne - Nazwa kategorii (np. "Biustonosze", "Sukienki")
- `--max`, `-m`: Opcjonalne - Maksymalna liczba produktów (domyślnie 5)

## Filtry automatyczne

Automatyzacja zawsze stosuje następujące filtry:
- `active = True` - tylko aktywne produkty
- `is_mapped = False` - tylko niezmapowane produkty

## Przykłady marki i kategorii

### Popularne marki:
- Axami
- DKaren
- Lupo Line
- Stylove
- 4F
- Atlantic

### Popularne kategorie:
- Biustonosze
- Sukienki
- Piżamy
- Stroje kąpielowe
- Koszulki

## Monitorowanie

### W trakcie działania:
- Przeglądarka Chrome będzie widoczna
- Zobaczysz postęp w konsoli

### Po zakończeniu:
```
http://localhost:8000/admin/web_agent/automationrun/
```

## Zmienne środowiskowe

Upewnij się, że masz w `.env.dev`:

```env
DJANGO_ADMIN_USERNAME=Web_Agent
DJANGO_ADMIN_PASSWORD=twoje_haslo
WEB_AGENT_BASE_URL=http://localhost:8000
OPENAI_API_KEY=sk-...
BROWSER_HEADLESS=False  # True dla trybu bez okna
```

## Troubleshooting

### "Brak produktów spełniających kryteria"
- Sprawdź czy nazwa marki/kategorii jest poprawna
- Sprawdź czy są produkty z `active=True` i `is_mapped=False`

### "Błąd logowania"
- Sprawdź DJANGO_ADMIN_USERNAME i DJANGO_ADMIN_PASSWORD
- Sprawdź czy użytkownik istnieje w bazie

### "OpenAI API error"
- Sprawdź OPENAI_API_KEY
- Sprawdź limit API (quota)

### Przeglądarka nie zamyka się
- Zatrzymaj przez Ctrl+C
- Lub ustaw BROWSER_HEADLESS=True

