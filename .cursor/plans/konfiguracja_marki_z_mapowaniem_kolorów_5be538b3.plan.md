---
name: Konfiguracja marki z mapowaniem kolorów
overview: Utworzenie systemu konfiguracji dla każdej marki z mapowaniem kolorów producenta i domyślnymi ustawieniami. Każda marka będzie miała dedykowaną konfigurację przechowywaną w bazie danych.
todos: []
---

# Plan: Konfiguracja marki z mapowaniem kolorów

## Cel

Utworzenie systemu, gdzie każda marka ma dedykowaną konfigurację z:

- Mapowaniem kolorów producenta (np. "Dark Brown" → "Ciemny Brąz")
- Domyślnymi filtrami (active, is_mapped)
- Osobne AutomationRun dla każdej marki

## Implementacja

### 1. Nowy model BrandConfig

**Plik:** `web_agent/models.py`

Dodanie modelu `BrandConfig` z polami:

- `brand_id` (IntegerField) - ID marki z bazy matterhorn1
- `brand_name` (CharField) - Nazwa marki
- `default_active_filter` (BooleanField, null=True) - domyślny filtr active
- `default_is_mapped_filter` (BooleanField, null=True) - domyślny filtr is_mapped
- `color_mapping` (JSONField) - mapowanie kolorów producenta: `{"Dark Brown": "Ciemny Brąz", "Beige": "Beż", ...}`
- `created_at`, `updated_at` (DateTimeField)

### 2. Migracja bazy danych

**Plik:** `web_agent/migrations/XXXX_brand_config.py`

Utworzenie migracji dla nowego modelu `BrandConfig` w bazie `zzz_default`.

### 3. Admin interface dla BrandConfig

**Plik:** `web_agent/admin.py`

Dodanie `BrandConfigAdmin` z:

- `list_display`: brand_name, default_active_filter, default_is_mapped_filter
- `search_fields`: brand_name
- Edycja mapowania kolorów w formularzu (JSONField jako edytowalne pole)

### 4. Modyfikacja komendy run_automation

**Plik:** `web_agent/management/commands/run_automation.py`

Zmiany:

- Jeśli podano `--brand`, sprawdź czy istnieje `BrandConfig` dla tej marki
- Jeśli istnieje, użyj domyślnych filtrów z konfiguracji (jeśli nie podano w parametrach)
- Przekaż konfigurację marki do `ProductProcessor` (dla mapowania kolorów)

### 5. Modyfikacja ProductProcessor

**Plik:** `web_agent/automation/product_processor.py`

Zmiany:

- Dodanie parametru `brand_config` do `__init__`
- Metoda `map_producer_color(color_name: str) -> str`:
  - Jeśli istnieje mapowanie w `brand_config.color_mapping`, zwróć zmapowaną nazwę
  - W przeciwnym razie zwróć oryginalną nazwę
- Użycie mapowania w `prepare_mpd_form_data()` dla pola `producer_color_name`

### 6. Aktualizacja AutomationRun

**Plik:** `web_agent/models.py` (opcjonalnie)

Możliwość dodania pola `brand_config_id` do `AutomationRun` dla lepszego śledzenia, ale nie jest to wymagane (można użyć `brand_id`).

## Przykład użycia

```bash
# Uruchomienie z marką (użyje konfiguracji marki jeśli istnieje)
python manage.py run_automation --brand "Marko" --settings=nc.settings.dev

# Jeśli marka ma konfigurację:
# - Zastosuje domyślne filtry z BrandConfig
# - Zmapuje kolory producenta zgodnie z color_mapping
# - Ulepszy i sformatuje opis produktu przez AI
# - Wyszuka atrybuty w opisie używając embeddings + cosine similarity
# - Automatycznie zaznaczy znalezione atrybuty w formularzu MPD
```

## Technologie ML

- **sentence-transformers** - generowanie embeddings (model: 'all-MiniLM-L6-v2' lub podobny)
- **cosine similarity** - obliczanie podobieństwa między embeddings
- **Celery taski ML** - wykonywane w kontenerze `celery-ml` (kolejka 'ml')
- **Próg podobieństwa** - domyślnie 0.7 (70%), konfigurowalny w BrandConfig

## Zarządzanie konfiguracjami

Konfiguracje będą zarządzane przez Django Admin:

- `/admin/web_agent/brandconfig/` - lista konfiguracji
- Możliwość dodania/edycji mapowania kolorów dla każdej marki
- Domyślne filtry można ustawić dla każdej marki osobno

## Zalety rozwiązania

1. **Osobna konfiguracja** - każda marka ma własne ustawienia
2. **Mapowanie kolorów** - automatyczne tłumaczenie nazw kolorów producenta
3. **Domyślne filtry** - każda marka może mieć inne domyślne wartości
4. **Elastyczność** - można nadpisać filtry przez parametry komendy
5. **Osobne AutomationRun** - każda marka ma osobny log w bazie