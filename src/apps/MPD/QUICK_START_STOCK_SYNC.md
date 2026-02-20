# Quick Start - Synchronizacja stanów magazynowych

## 1. Szybki start - Uruchom task ręcznie

```bash
# Aktywuj środowisko wirtualne
.\.venv\Scripts\Activate.ps1

# Uruchom Django shell
cd src && python manage.py shell --settings=core.settings.dev
```

```python
# W Django shell:
from MPD.tasks import update_stock_from_matterhorn1

# Uruchom synchronizację (domyślnie sprawdza ostatnie 15 minut)
result = update_stock_from_matterhorn1.delay()

# Lub z własnym oknem czasowym (np. 30 minut)
result = update_stock_from_matterhorn1.delay(time_window_minutes=30)

# Sprawdź status (opcjonalnie poczekaj na wynik)
print(result.status)
result_data = result.get(timeout=300)
print(result_data)
```

## 2. Konfiguracja automatyczna - Periodic Task

```bash
# Konfiguruj periodic task (domyślnie: co 5 minut, sprawdza ostatnie 15 minut)
python manage.py setup_stock_sync_task --settings=core.settings.dev

# Lub z własnymi ustawieniami:
python manage.py setup_stock_sync_task --interval 5 --time-window 15 --settings=core.settings.dev
```

Opcje:
- `--interval 5` - jak często uruchamiać task (domyślnie: 5 minut)
- `--time-window 15` - ile minut wstecz sprawdzać (domyślnie: 15 minut)
- `--disable` - wyłącz task
- `--delete` - usuń task

**Rekomendacja:** Task uruchamiany co 5 minut, sprawdza ostatnie 15 minut - dzięki temu masz bufor i nie przegapisz zmian.

## 3. Monitoring

### Flower (Celery monitoring)
Otwórz: http://localhost:5555

### Django Admin
Przejdź do: http://localhost:8000/admin/django_celery_beat/periodictask/

### Logi
```bash
# Development
tail -f logs/matterhorn/import_all_by_one.log
```

## 4. Wymagania przed uruchomieniem

### Mapowanie wariantów
Warianty w Matterhorn1 muszą być zmapowane:

```sql
-- Sprawdź zmapowane warianty
SELECT 
    pv.variant_uid,
    pv.product_id,
    pv.name as size,
    pv.stock,
    pv.mapped_variant_uid,
    pv.is_mapped
FROM productvariant pv
WHERE pv.is_mapped = true;
```

Jeśli brak zmapowanych wariantów, musisz najpierw je zmapować:

```python
from matterhorn1.models import ProductVariant
from MPD.models import ProductVariants

# Przykład mapowania
mh1_variant = ProductVariant.objects.using('zzz_matterhorn1').get(variant_uid='ABC123')
mpd_variant = ProductVariants.objects.using('zzz_MPD').get(variant_id=456)

# Ustaw mapowanie
mh1_variant.mapped_variant_uid = mpd_variant.variant_id
mh1_variant.is_mapped = True
mh1_variant.save(using='zzz_matterhorn1')
```

### Źródło w MPD
Task automatycznie utworzy źródło "Matterhorn API" jeśli nie istnieje.

## 5. Przykładowy wynik

```python
{
    'status': 'success',
    'task_id': 'abc-123-...',
    'message': 'Synchronizacja zakończona: 42 zaktualizowano, 5 utworzono',
    'stats': {
        'checked': 100,
        'updated': 42,
        'created': 5,
        'unchanged': 48,
        'errors': 5
    },
    'duration_seconds': 12.34,
    'start_time': '2024-01-15T10:30:00Z',
    'end_time': '2024-01-15T10:30:12Z'
}
```

## 6. Troubleshooting

### Brak zmapowanych wariantów
```
ℹ️ Brak zmapowanych wariantów do synchronizacji
```
**Rozwiązanie**: Zmapuj warianty (patrz punkt 4)

### Nie znaleziono wariantu MPD
```
⚠️ Nie znaleziono wariantu MPD dla mapped_variant_uid=123
```
**Rozwiązanie**: Sprawdź czy wariant istnieje w MPD i czy ma rekord w ProductvariantsSources

### Błąd połączenia z bazą
**Rozwiązanie**: Sprawdź czy:
- PostgreSQL działa
- Settings.dev ma poprawną konfigurację baz danych
- Masz dostęp do obu baz (zzz_matterhorn1 i zzz_MPD)

## 7. Pełna dokumentacja

Zobacz `MPD_STOCK_SYNC_README.md` dla pełnej dokumentacji.

