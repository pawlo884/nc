# Raw SQL – analiza i rekomendacje zamiany na Django ORM

## 1. Należy zamienić na ORM (priorytet wysoki)

### MPD/signals.py
- **SELECT variant_id** (linie 108–116) → `ProductVariants.objects.using(mpd_db).filter(product_id=instance.id).values_list('variant_id', flat=True)`
- **UPDATE product** (linie 123–134) → `Product.objects.using(mh_db).filter(mapped_product_uid=instance.id).update(mapped_product_uid=None, is_mapped=False, updated_at=timezone.now())`
- **UPDATE productvariant** (linie 138–146) → `ProductVariant.objects.using(mh_db).filter(mapped_variant_uid__in=variant_ids).update(...)`
- **UPDATE tabu_product_detail** (linie 157–164) → `TabuProduct.objects.using(tabu_db).filter(mapped_product_uid=instance.id).update(mapped_product_uid=None)`

### MPD/views.py
- **products()** (linie 36–66) – SELECT z JOIN na product_variants, sizes, colors, stock_and_prices → użyć ORM z `select_related`/`prefetch_related`, `ProductVariants.objects.using('MPD').filter(product_id__in=product_ids).select_related('size', 'color')` + `StockAndPrices.objects.filter(variant_id__in=...)`

### MPD/admin.py
- **Linie 679–684** – `SELECT variant_id, source_id, stock, price FROM stock_and_prices` → `StockAndPrices.objects.using('MPD').filter(variant_id__in=variant_ids).values('variant_id', 'source_id', 'stock', 'price', 'currency')`

### tabu/admin.py (change_view)
- **Linie 174–196** – SELECT colors, path, attributes, brands, units, sizes, fabric_component → modele MPD: `Colors.objects.using('MPD')`, `ProductPaths.objects.using('MPD')` itd.
- **Linie 208–241** – SELECT produktu, wariantów, path_id, attribute_id → ORM z `select_related`

### web_agent/automation/product_processor.py
- **get_product_data** (linie 42–59) – SELECT product + LEFT JOIN brand, category → `Product.objects.using('matterhorn1').select_related('brand', 'category').get(id=product_id)`
- **get_product_variants** (linie 99–119) → `ProductVariant.objects.using('matterhorn1').filter(product_id=product_id).values(...)`

### matterhorn1/stock_tracker.py
- **track_stock_change** (linie 40–51) – SELECT p.name, pv.name → `Product.objects.using('matterhorn1').select_related(...).get(product_uid=..., productvariant__variant_uid=...)`
- **get_stock_trends** (linie 125–155) → `StockHistory.objects.using('matterhorn1').filter(product_uid=..., timestamp__gte=...).values(...)`
- **get_popular_products** (linie 193–210) → `StockHistory.objects.filter(change_type='decrease', ...).values('product_uid', 'product_name').annotate(...)`
- **cleanup_old_stock_history** → `StockHistory.objects.filter(timestamp__lt=...).delete()`

---

## 2. Możliwa zamiana (priorytet średni)

### matterhorn1/admin.py
- Dużo raw SQL dla cross-database (MPD + matterhorn1), złożona logika mapowań.
- Część można zastąpić ORM (np. pobieranie list kolorów, rozmiarów, path, attributes), ale wymaga refaktoryzacji.

### matterhorn1/saga.py
- Saga z INSERT/UPDATE między bazami.
- Można stopniowo zamieniać proste SELECT/UPDATE na ORM, zostawiając skomplikowane operacje.

### matterhorn1/database_utils.py
- Funkcje pomocnicze – sprawdzić, czy modele są zarejestrowane i czy ORM da się użyć.

### web_agent/automation/background_automation.py, browser_automation.py
- Wymaga przejrzenia zapytań – prawdopodobnie da się zamienić na ORM.

---

## 3. Zostawić jako raw SQL (nie zamieniać)

| Plik | Powód |
|------|-------|
| **Migracje** (MPD/0005, matterhorn1/0003) | ALTER TABLE, RENAME, sekwencje – ORM nie obsługuje |
| **MPD/defs_db.py** | DDL: CREATE TABLE, trigger, function |
| **MPD/create_mpd_db.py** | CREATE DATABASE |
| **MPD/init_iai_counter.py** | Inicjalizacja sekwencji, CREATE SEQUENCE |
| **matterhorn1/saga_variants.py** (iai_product_counter) | `INSERT ... ON CONFLICT DO UPDATE` – PostgreSQL-specific, ORM ma `update_or_create` ale dla innego przypadku |
| **MPD/views.py** (test_connection, test_table_structure) | Zapytania do `information_schema` – ORM nie wspiera |
| **tabu/management/commands/check_tabu_mpd_db.py** | `SELECT 1` – prosty health check |
| **MPD/create_full_change_files_db.py** | Wykonanie dynamicznego DDL |
| **Komentarze w signals.py** (linie 22–54) | Zakomentowany kod |

---

## 4. Szczegóły – iai_product_counter (saga_variants.py)

```sql
INSERT INTO iai_product_counter (id, counter_value) VALUES (1, 1)
ON CONFLICT (id) DO UPDATE SET counter_value = iai_product_counter.counter_value + 1
RETURNING counter_value
```

Opcje:
- **Opcja A:** Model `IaiProductCounter` + `update_or_create` + ręczny increment (race condition przy równoległości).
- **Opcja B:** Raw SQL – rekomendowane dla atomicznego increment.
- **Opcja C:** `F('counter_value') + 1` w `update()` – wymaga wcześniejszego `get_or_create`, może być ryzykowne przy równoległości.

---

## 5. Podsumowanie – kolejność zamiany

1. **MPD/signals.py** – UPDATE i SELECT można zastąpić ORM (testy integracyjne już pokrywają sygnały).
2. **MPD/admin.py** – stock_and_prices (krótki SELECT).
3. **MPD/views.py** – products() – główny widok listy produktów.
4. **tabu/admin.py** – listy do selectów w change_view.
5. **web_agent/product_processor.py** – get_product_data, get_product_variants.
6. **matterhorn1/stock_tracker.py** – StockHistory i Product/ProductVariant.
7. **matterhorn1/admin.py**, **saga.py** – stopniowo, po ustabilizowaniu powyższych.
