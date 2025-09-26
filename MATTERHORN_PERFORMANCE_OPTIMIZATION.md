# Optymalizacja wydajności aplikacji Matterhorn

## Wprowadzone optymalizacje

### 1. **Dodane indeksy w modelach**

#### Model Products:
- `active` - dla filtrowania aktywnych produktów
- `category_name` - dla filtrowania po kategorii
- `brand` - dla filtrowania po marce
- `is_mapped` - dla sprawdzania statusu mapowania
- `mapped_product_id` - dla wyszukiwania zmapowanych produktów
- `last_updated` - dla zadań okresowych
- `timestamp` - dla sortowania chronologicznego
- `category_id`, `brand_id` - dla relacji
- **Złożone indeksy:**
  - `(active, category_name)` - dla często używanych kombinacji filtrów
  - `(is_mapped, mapped_product_id)` - dla sprawdzania mapowania

#### Model Images:
- `product` - dla relacji z produktami
- `timestamp` - dla sortowania chronologicznego

#### Model Variants:
- `product` - dla relacji z produktami
- `is_mapped` - dla sprawdzania statusu mapowania
- `mapped_variant_id` - dla wyszukiwania zmapowanych wariantów
- `last_updated` - dla zadań okresowych
- `timestamp` - dla sortowania chronologicznego
- `ean` - dla wyszukiwania po kodzie EAN
- **Złożone indeksy:**
  - `(product, is_mapped)` - dla sprawdzania mapowania wariantów
  - `(last_updated, product)` - dla zadań okresowych

### 2. **Optymalizacja zapytań Django**

#### Views (matterhorn/views.py):
- Dodano `select_related()` i `prefetch_related()` w widoku `products()`
- Prefetch dla: `images`, `variants`, `other_colors`

#### Admin (matterhorn/admin.py):
- Dodano `select_related()` i `prefetch_related()` w `get_queryset()`
- Prefetch dla: `images`, `variants`, `other_colors__color_product`, `product_in_set__set_product`
- **Cache dla brand_choices** - 5 minut cache dla list marek

### 3. **Optymalizacja zadań Celery**

#### Task `update_is_mapped_status`:
- **Bulk operations** zamiast pojedynczych zapytań
- **Prefetch related** dla wszystkich potrzebnych relacji
- **Batch update** z `bulk_update()` (batch_size=100)
- **Optymalizacja zapytań do MPD** - jedno zapytanie dla wszystkich mapped_product_id

### 4. **Instrukcje wdrożenia**

#### Krok 1: Utworzenie migracji
```bash
python manage.py makemigrations matterhorn --name add_performance_indexes
```

#### Krok 2: Zastosowanie migracji
```bash
python manage.py migrate matterhorn
```

#### Krok 3: Sprawdzenie indeksów w bazie
```sql
-- Sprawdzenie indeksów dla tabeli products
\d+ products

-- Sprawdzenie indeksów dla tabeli variants
\d+ variants

-- Sprawdzenie indeksów dla tabeli images
\d+ images
```

### 5. **Oczekiwane korzyści**

#### Wydajność:
- **50-80% szybsze** zapytania filtrujące po kategorii/marce
- **70-90% szybsze** ładowanie list produktów w admin
- **60-80% szybsze** zadania Celery (bulk operations)
- **Redukcja N+1 queries** dzięki prefetch_related

#### Obciążenie bazy:
- **Mniejsze obciążenie CPU** dzięki indeksom
- **Mniejsze zużycie pamięci** dzięki cache
- **Szybsze zapytania** dzięki złożonym indeksom

### 6. **Monitorowanie wydajności**

#### Sprawdzenie zapytań:
```python
# W Django shell
from django.db import connection
from matterhorn.models import Products

# Włącz logging zapytań
import logging
logging.basicConfig(level=logging.DEBUG)

# Test zapytania
products = Products.objects.filter(active='1', category_name='Odzież').prefetch_related('images', 'variants')
list(products)

# Sprawdź liczbę zapytań
print(f"Liczba zapytań: {len(connection.queries)}")
```

#### Sprawdzenie indeksów:
```sql
-- Analiza planu wykonania zapytania
EXPLAIN ANALYZE SELECT * FROM products WHERE active = '1' AND category_name = 'Odzież';

-- Sprawdzenie użycia indeksów
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch 
FROM pg_stat_user_indexes 
WHERE tablename IN ('products', 'variants', 'images')
ORDER BY idx_scan DESC;
```

### 7. **Dodatkowe rekomendacje**

#### Cache Redis:
- Rozważ dodanie cache dla często używanych zapytań
- Cache dla statystyk i raportów

#### Database connection pooling:
- Skonfiguruj connection pooling dla PostgreSQL
- Ustaw odpowiednie limity połączeń

#### Monitoring:
- Dodaj monitoring zapytań powolnych (>1s)
- Monitoruj użycie indeksów
- Sprawdzaj cache hit ratio

### 8. **Rollback (w razie problemów)**

```bash
# Cofnięcie migracji
python manage.py migrate matterhorn 0007

# Usunięcie indeksów ręcznie (jeśli potrzeba)
# ALTER TABLE products DROP INDEX IF EXISTS products_active_idx;
# ALTER TABLE products DROP INDEX IF EXISTS products_category_name_idx;
# itd.
```
