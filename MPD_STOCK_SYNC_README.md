# Synchronizacja stanów magazynowych MPD z Matterhorn1

## Opis

Task Celery `update_stock_from_matterhorn1` synchronizuje stany magazynowe z bazy danych Matterhorn1 do bazy MPD. 

**Kluczowa optymalizacja:** Task sprawdza tylko warianty zaktualizowane w określonym oknie czasowym (domyślnie ostatnie 15 minut), co znacznie zwiększa wydajność.

## Proces synchronizacji

1. **Pobiera zmapowane warianty** z `matterhorn1.ProductVariant` gdzie:
   - `is_mapped=True` 
   - `mapped_variant_uid` jest ustawione
   - `updated_at >= (current_time - time_window_minutes)` - tylko ostatnie X minut
2. **Znajduje odpowiednie warianty** w MPD używając `mapped_variant_uid` jako klucza
3. **Aktualizuje `StockAndPrices`** w MPD nowymi stanami z Matterhorn1
4. **Loguje zmiany** do `StockHistory` dla każdej zmiany stanu
5. **Zwraca statystyki** z podsumowaniem operacji

## Okno czasowe (Time Window)

- **Domyślnie:** 15 minut wstecz od momentu uruchomienia taska
- **Konfiguracja:** parametr `time_window_minutes` przy uruchamianiu taska
- **Rekomendacja:** Task co 5 minut, okno 15 minut = 3x bufor bezpieczeństwa

## Wymagania

### Mapowanie wariantów

Aby synchronizacja działała, warianty w Matterhorn1 muszą być zmapowane do wariantów w MPD:

```python
# W matterhorn1.ProductVariant:
- is_mapped = True
- mapped_variant_uid = <variant_id z MPD.ProductVariants>
```

### Źródło w MPD

Task automatycznie znajdzie lub utworzy źródło "Matterhorn API" w tabeli `Sources`.

## Uruchomienie ręczne

### Z Django shell

```bash
python manage.py shell --settings=nc.settings.dev
```

```python
from MPD.tasks import update_stock_from_matterhorn1

# Uruchom synchronizację (domyślnie: ostatnie 15 minut)
result = update_stock_from_matterhorn1.delay()

# Uruchom z własnym oknem czasowym (np. ostatnie 30 minut)
result = update_stock_from_matterhorn1.delay(time_window_minutes=30)

# Uruchom dla wszystkich zmapowanych wariantów (bardzo długie!)
result = update_stock_from_matterhorn1.delay(time_window_minutes=999999)

# Sprawdź status
print(result.status)

# Poczekaj na wynik
result_data = result.get(timeout=300)
print(result_data)
```

### Z Celery CLI

```bash
# Uruchom task
celery -A nc call MPD.tasks.update_stock_from_matterhorn1

# Lub z flower (http://localhost:5555)
```

## Periodic Task (automatyczne uruchamianie)

### Szybka konfiguracja (REKOMENDOWANE)

```bash
# Domyślnie: co 5 minut, sprawdza ostatnie 15 minut
python manage.py setup_stock_sync_task --settings=nc.settings.dev

# Własne ustawienia:
python manage.py setup_stock_sync_task --interval 5 --time-window 15 --settings=nc.settings.dev

# Wyłącz task
python manage.py setup_stock_sync_task --disable --settings=nc.settings.dev

# Usuń task
python manage.py setup_stock_sync_task --delete --settings=nc.settings.dev
```

### Konfiguracja w Django Admin

1. Przejdź do `/admin/django_celery_beat/periodictask/`
2. Kliknij "Add Periodic Task"
3. Wypełnij:
   - **Name**: `Synchronizacja stanów MPD z Matterhorn1`
   - **Task**: `MPD.tasks.update_stock_from_matterhorn1`
   - **Interval**: Stwórz nowy interval (np. co 5 minut)
   - **Keyword arguments**: `{"time_window_minutes": 15}` (JSON)
   - **Enabled**: ✓

### Konfiguracja programowa

```python
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils import timezone
import json

# Stwórz interval (co 5 minut)
schedule, created = IntervalSchedule.objects.get_or_create(
    every=5,
    period=IntervalSchedule.MINUTES,
)

# Stwórz periodic task z oknem czasowym
PeriodicTask.objects.create(
    interval=schedule,
    name='Synchronizacja stanów MPD z Matterhorn1',
    task='MPD.tasks.update_stock_from_matterhorn1',
    kwargs=json.dumps({'time_window_minutes': 15}),
    enabled=True,
    start_time=timezone.now()
)
```

### Rekomendowane ustawienia

| Wielkość sklepu | Interval | Time Window | Opis |
|----------------|----------|-------------|------|
| Mały (<1000)   | 5 min    | 15 min      | Szybkie reakcje na zmiany |
| Średni (1k-5k) | 5 min    | 15 min      | Balans między wydajnością a aktualnością |
| Duży (>5k)     | 10 min   | 20 min      | Mniej częste, ale bardziej wydajne |

**Dlaczego time_window > interval?**
- Bufor bezpieczeństwa (np. 3x)
- Nie przegapisz zmian jeśli task się opóźni
- Pokrycie dla overlapping updates

## Zwracane dane

Task zwraca słownik z następującymi informacjami:

```python
{
    'status': 'success',  # 'success', 'partial', 'warning', 'failure'
    'task_id': 'abc-123-...',
    'message': 'Synchronizacja zakończona: 42 zaktualizowano, 5 utworzono',
    'stats': {
        'checked': 100,        # Ile wariantów sprawdzono
        'updated': 42,         # Ile stanów zaktualizowano
        'created': 5,          # Ile nowych rekordów utworzono
        'unchanged': 48,       # Ile stanów nie zmieniło się
        'errors': 5,           # Ile błędów wystąpiło
        'error_details': [...]  # Lista komunikatów błędów (max 10)
    },
    'duration_seconds': 12.34,
    'start_time': '2024-01-15T10:30:00Z',
    'end_time': '2024-01-15T10:30:12Z'
}
```

## Logowanie

Task loguje informacje do loggera Django:

```python
import logging
logger = logging.getLogger(__name__)
```

### Przykładowe logi

```
INFO: 🚀 Rozpoczynam task update_stock_from_matterhorn1 (ID: abc-123)
INFO: 📊 Znaleziono 100 zmapowanych wariantów w matterhorn1
INFO: ✨ Utworzono nowy rekord StockAndPrices dla wariantu 42: stock=10
INFO: 🔄 Zaktualizowano stan dla wariantu 43: 5 → 8
INFO: ✅ Task update_stock_from_matterhorn1 (ID: abc-123) zakończony w 12.34s
INFO: 📊 Statystyki:
INFO:    - Sprawdzono: 100
INFO:    - Zaktualizowano: 42
INFO:    - Utworzono: 5
INFO:    - Bez zmian: 48
INFO:    - Błędy: 5
```

## Obsługa błędów

### Częste problemy

#### 1. Brak zmapowanych wariantów

```
ℹ️ Brak zmapowanych wariantów do synchronizacji
```

**Rozwiązanie**: Upewnij się, że warianty w Matterhorn1 mają:
- `is_mapped = True`
- `mapped_variant_uid` ustawiony na prawidłowy `variant_id` z MPD

#### 2. Nie znaleziono wariantu MPD

```
⚠️ Nie znaleziono wariantu MPD dla mapped_variant_uid=123
```

**Rozwiązanie**: 
- Sprawdź czy wariant o ID 123 istnieje w `MPD.ProductVariants`
- Sprawdź czy istnieje rekord w `MPD.ProductvariantsSources` dla źródła Matterhorn

#### 3. Brak źródła Matterhorn

```
⚠️ Brak źródła Matterhorn - pomijam synchronizację
```

**Rozwiązanie**: Task automatycznie tworzy źródło, ale jeśli to nie działa, utwórz je ręcznie:

```python
from MPD.models import Sources

Sources.objects.create(
    name='Matterhorn API',
    type='api',
    location='https://api.matterhorn.pl'
)
```

## Monitoring

### Flower (Celery monitoring)

Otwórz http://localhost:5555 aby:
- Zobaczyć status tasków
- Sprawdzić historię wykonań
- Zobaczyć szczegóły błędów

### Django Admin

1. Przejdź do `/admin/django_celery_results/taskresult/`
2. Znajdź task `MPD.tasks.update_stock_from_matterhorn1`
3. Zobacz szczegóły wykonania i wyniki

### Logi

```bash
# Development
tail -f logs/matterhorn/import_all_by_one.log

# Docker
docker-compose logs -f celery_worker
```

## Historia zmian stanów

Wszystkie zmiany stanów są zapisywane w `MPD.StockHistory`:

```sql
SELECT 
    sh.*,
    pv.producer_code,
    p.name as product_name
FROM stock_history sh
JOIN product_variants pv ON sh.stock_id = pv.variant_id
JOIN products p ON pv.product_id = p.id
WHERE sh.source_id = (SELECT id FROM sources WHERE name LIKE '%Matterhorn%')
ORDER BY sh.change_date DESC
LIMIT 50;
```

## Testowanie

### Test jednostkowy

```python
from django.test import TransactionTestCase
from MPD.tasks import update_stock_from_matterhorn1
from matterhorn1.models import ProductVariant as Mh1Variant
from MPD.models import StockAndPrices, Sources

class StockSyncTestCase(TransactionTestCase):
    databases = ['zzz_matterhorn1', 'zzz_MPD']
    
    def test_update_stock(self):
        # Przygotuj dane testowe
        # ... (stwórz warianty z mapowaniem)
        
        # Uruchom task
        result = update_stock_from_matterhorn1()
        
        # Sprawdź wynik
        self.assertEqual(result['status'], 'success')
        self.assertGreater(result['stats']['checked'], 0)
```

## Performance

### Optymalizacja

Task używa:
- **Time window filtering** - sprawdza tylko ostatnie X minut (ogromny wzrost wydajności!)
- `select_related('product')` dla matterhorn1 variants
- `select_related('variant')` dla MPD variant sources
- Batch processing (wszystkie operacje w jednej transakcji per wariant)
- Index na `updated_at` w matterhorn1.ProductVariant (ważne!)

### Szacowany czas wykonania

#### Z time window (15 minut):
- Typowe obciążenie: ~1-5 sekund (tylko zmienione warianty)
- Duże obciążenie: ~10-30 sekund (wiele zmian jednocześnie)

#### Bez time window (wszystkie warianty):
- 100 wariantów: ~5-10 sekund
- 1000 wariantów: ~30-60 sekund
- 10000 wariantów: ~5-10 minut

### Impact time window

Przykład: sklep z 10 000 wariantów, typowo 50 zmian na godzinę:

| Time window | Warianty do sprawdzenia | Czas wykonania |
|-------------|------------------------|----------------|
| 5 minut     | ~4 warianty            | <1 sekunda     |
| 15 minut    | ~12 wariantów          | ~1 sekunda     |
| 60 minut    | ~50 wariantów          | ~5 sekund      |
| Bez limitu  | 10 000 wariantów       | ~5-10 minut    |

**Wniosek:** Time window daje ~1000x przyspieszenie! 🚀

## Bezpieczeństwo

- Task używa `using(database)` dla wszystkich operacji na bazach danych
- Wszystkie błędy są przechwytywane i logowane
- Transaction rollback w przypadku błędów krytycznych
- Limit szczegółów błędów do 10 aby nie przeciążyć logów

## Powiązane taski

- `export_full_change_xml_full` - eksport XML z MPD (używa zaktualizowanych stanów)
- `track_recent_stock_changes` - TODO: analiza zmian stanów

## TODO / Przyszłe ulepszenia

- [ ] Batch updates dla większej wydajności (bulk_update)
- [ ] Retry logic dla błędów sieciowych
- [ ] Webhook notifications dla dużych zmian stanów
- [ ] Delta updates (tylko zmienione warianty)
- [ ] Compression dla dużych synchronizacji
- [ ] Parallel processing dla bardzo dużych zbiorów danych

