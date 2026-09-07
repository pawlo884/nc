# Matterhorn1 — dokumentacja aplikacji

Import katalogu i stanów magazynowych z hurtowni **Matterhorn** (`matterhorn.pl`,
B2BAPI) do własnej bazy-lustra, skąd dane trafiają do MPD i dalej do IdoSell.

Stan: v1.44.12+ (2026-09-06). Zastępuje starsze notatki
[`MATTERHORN1_SIMPLE_CELERY.md`](MATTERHORN1_SIMPLE_CELERY.md),
[`MATTERHORN1_SMART_IMPORT.md`](MATTERHORN1_SMART_IMPORT.md),
[`MATTERHORN1_CELERY_TASKS.md`](MATTERHORN1_CELERY_TASKS.md) — one opisują
wcześniejsze, częściowo nieaktualne warianty tego samego systemu.

## Spis

- [1. Przegląd i miejsce w systemie](#1-przegląd-i-miejsce-w-systemie)
- [2. Model danych](#2-model-danych)
- [3. Bazy danych i routing](#3-bazy-danych-i-routing)
- [4. Import — pełny obraz](#4-import--pełny-obraz)
- [5. Pipeline pobierania stron](#5-pipeline-pobierania-stron)
- [6. Krok ITEMS](#6-krok-items)
- [7. Krok INVENTORY](#7-krok-inventory)
- [8. Wznawianie i checkpoint](#8-wznawianie-i-checkpoint)
- [9. Harmonogram (celery-beat) i watchdog](#9-harmonogram-celery-beat-i-watchdog)
- [10. StockHistory i most do MPD](#10-stockhistory-i-most-do-mpd)
- [11. Admin](#11-admin)
- [12. Znane problemy i pułapki](#12-znane-problemy-i-pułapki)
- [13. Testy](#13-testy)
- [14. Komendy zarządzania](#14-komendy-zarządzania)
- [15. Historia zmian (istotne PR-y)](#15-historia-zmian-istotne-pr-y)

---

## 1. Przegląd i miejsce w systemie

```
Matterhorn B2BAPI ──(import)──▶ baza matterhorn1 ──(most stanów / mapowanie)──▶ MPD ──▶ eksport IOF/Presta ──▶ IdoSell
   /B2BAPI/ITEMS/             (Brand, Category, Product,     MPD.tasks.update_stock_from_matterhorn1
   /B2BAPI/ITEMS/INVENTORY/    ProductVariant, ...)          + ręczne mapowanie w adminie
```

- **ITEMS** — pełny katalog: produkty, marki, kategorie, warianty (rozmiary),
  zdjęcia, ceny, szczegóły. **Nie pokazuje stanów 0.**
- **INVENTORY** — same stany magazynowe per wariant, **w tym zera**. Dlatego
  po każdym imporcie ITEMS leci krok INVENTORY.
- Limit API: **2 requesty/sekundę** (udokumentowany przez Matterhorn).
- Uwierzytelnianie: nagłówek `Authorization: <MATTERHORN_API_KEY>`
  (fallback `username:password`). Konfiguracja: `MATTERHORN_API_URL`,
  `MATTERHORN_API_KEY` (ew. `MATTERHORN_API_USERNAME`/`_PASSWORD`) w `.env`.

Matterhorn to jedna z trzech działających hurtowni (obok `tabu` i `mada`);
`wega` jest w fazie R&D. Kod: `src/apps/matterhorn1/`.

---

## 2. Model danych

`src/apps/matterhorn1/models.py`. Tabele bez prefiksu (`brand`, `product`, …)
poza `matterhorn1_stock_history`.

| Model               | Tabela                      | Rola                                            | Klucz z API                                     |
| ------------------- | --------------------------- | ----------------------------------------------- | ----------------------------------------------- |
| `Brand`             | `brand`                     | marka                                           | `brand_id` (unique)                             |
| `Category`          | `category`                  | kategoria + `path`                              | `category_id` (unique)                          |
| `Product`           | `product`                   | produkt                                         | `product_uid` (IntegerField, **unique**)        |
| `ProductDetails`    | `productdetails`            | 1:1 — waga, tabela rozmiarów                    | —                                               |
| `ProductImage`      | `productimage`              | zdjęcia, `unique(product, image_url)`           | —                                               |
| `ProductVariant`    | `productvariant`            | wariant/rozmiar, **`stock`**                    | `variant_uid` (CharField, **unique globalnie**) |
| `ApiSyncLog`        | `apisynclog`                | log + **checkpoint** (`current_page`, `status`) | —                                               |
| `StockHistory`      | `matterhorn1_stock_history` | historia zmian stanu                            | —                                               |
| `Saga` / `SagaStep` | `saga_logs` / `saga_steps`  | saga mapowania do MPD (`core.saga`)             | —                                               |

Mapowanie do MPD: `Product.mapped_product_uid` / `is_mapped`,
`ProductVariant.mapped_variant_uid` / `is_mapped`. Ustawiane ręcznie w adminie
(`mpd_create` / `assign_mapping`, wspólny `core/wholesaler_admin/`) albo
automatycznie po EAN.

`ApiSyncLog` dla importu ITEMS ma `sync_type='items_import'`; pole
`current_page` to numer strony, od której wznowić przerwany import (patrz §8).

---

## 3. Bazy danych i routing

Router `core/db_routers.py` (`Matterhorn1Router`) kieruje wszystkie modele
`app_label == 'matterhorn1'` do aliasu z `_get_matterhorn1_db()`:

- **produkcja:** `matterhorn1`
- **dev / staging / testy:** `zzz_matterhorn1` (na dev oba aliasy wskazują tę
  samą fizyczną bazę za tunelem SSH `postgres-ssh-tunnel:5434`)
- **testy pytest:** `DATABASE_ROUTERS = []`, a `zzz_matterhorn1` ma
  `TEST = {'MIRROR': 'default'}` — bez jawnego `.using()` zapytania idą do
  `default`. Kod importu używa **na sztywno `.using('matterhorn1')`** — w
  testach ten alias też mirroruje `default`.

⚠️ Część kodu (`core.saga`, admin) używa `_get_matterhorn1_db()`, część —
literału `'matterhorn1'`. Na prod/dev to jedno i to samo; w testach trzeba
pilnować, którego aliasu użyć w fixture (patrz [`../TESTING.md`](../TESTING.md),
[`project_testing_pytest`](../../memory) w pamięci).

---

## 4. Import — pełny obraz

Jeden task steruje wszystkim:

**`matterhorn1.tasks.full_import_and_update`** (`@shared_task`, kolejka
`import`, worker `celery-heavy` z `-Q import,heavy` concurrency 2).

```
full_import_and_update(start_id=None, max_products=200000, api_url=None,
                       username=None, password=None, batch_size=100,
                       dry_run=False, auto_continue=True)
```

Przebieg:

1. `_check_database_connection()` — retry x3, przerwij jak baza niedostępna.
2. **Blokada:** `advisory_lock('matterhorn1:full_import_and_update')` — PostgreSQL
   advisory lock (`core.pg_locks`, jak `tabu`). Zwalnia się sam po padzie workera,
   bez TTL i ghost-locków. Nie zdobyta → `return {'status': 'skipped', 'reason': 'already_running'}`.
   Dekorator taska: `acks_late=False` — ubity w połowie run **nie** jest
   redeliverowany po `visibility_timeout` (1 h); kolejny tick beat wznawia od
   `current_page`.
3. `_fail_stale_running_imports()` — trzymamy wyłączny lock, więc każdy rekord
   `items_import` w statusie `running` to sierota po ubitym workerze → `error`
   (`current_page` zostaje do wznowienia).
4. `_run_full_import_locked(...)` — właściwe ciało importu.
5. Pętla iteracji (`while True`, bezpiecznik 100 iteracji):
   - **KROK 1 — ITEMS:** `_import_products_from_items(...)`.
     - `status == 'completed'` (koniec danych) → zrób ostatni INVENTORY i `break`.
     - `status == 'error'` → zapamiętaj błąd i `break` (**nie** kończ jako
       'completed' — `current_page` zostaje do wznowienia).
     - `status == 'success'` (osiągnięto `max_products`) → leć dalej.
   - **KROK 2 — INVENTORY:** `_update_inventory_from_api(...)`.
   - `imported_count == 0` albo `auto_continue == False` → `break`.
6. Zapisz `ApiSyncLog` (`success` / `completed` / `error` / `inventory_failed`),
   `return {'status': 'success'|'error'|'partial', 'total_imported', 'total_updated', ...}`.
   Advisory lock zwalnia context manager.

`dry_run=True` — pobiera z API i liczy, ale **nie** pisze do bazy i nie
aktualizuje `ApiSyncLog`.

---

## 5. Pipeline pobierania stron

Wspólny wzorzec dla ITEMS i INVENTORY (`_import_products_from_items` /
`_update_inventory_from_api`). Stałe modułowe:
`MATTERHORN_PAGE_LAUNCH_INTERVAL = 2.0`, `MATTERHORN_PIPELINE_MAX_WORKERS = 50`.

**Problem:** pojedyncza strona `?page=N` odpowiada 30–90 s (wolne, zewnętrzne
API; pod obciążeniem współbieżnym jeszcze wolniej). Sekwencyjnie: godzina+.

**Rozwiązanie — pipeline:**

- **Wątek launcher** (`_launcher`, `threading.Thread`) wystrzeliwuje nową
  stronę **co ~2 s**, niezależnie od tempa zapisu. Bez limitu okna — leci aż do
  końca danych / błędu. Górna granica wątków (50) to tylko zabezpieczenie.
- Odpowiedzi trafiają do bufora `pending` (`{page: Future}`), chronionego
  `threading.Lock`.
- **Wątek główny** konsumuje wyniki **ŚCIŚLE w kolejności stron** — stronę N+1
  zapisuje dopiero po zapisaniu N. Inaczej wznowienie po awarii mogłoby
  pominąć stronę, która akurat odpowiedziała później.
- **Wczesny stop:** launcher przestaje strzelać, gdy **którakolwiek** już
  gotowa strona w buforze okaże się końcem danych / błędem (puste strony
  odpowiadają szybko — bez tego launcher leciał dziesiątki stron za koniec
  danych, marnując requesty).
- Kontekst zadania Celery przekazany do wątków (`_run_with_task_context`), żeby
  logi z wątków miały `full_import_and_update[<task_id>]` zamiast `???[???]`.

Fetch pojedynczej strony (`_fetch_items_page` / `_fetch_inventory_page`):

- ITEMS: do 10 prób, 20 s między próbami; zwraca `{'outcome': 'ok'|'end_of_data'|'error'}`.
- INVENTORY: **bez retry** (historycznie tak było) — każdy błąd/koniec = `{'outcome': 'ok'|'stop'}`.

---

## 6. Krok ITEMS

`_import_products_from_items` → pipeline (§5) → `_bulk_import_products(items)`
per strona (w kolejności).

`_bulk_import_products` (batch, bez N+1):

1. `_resolve_brands_categories(items)` — batch `get_or_create` marek/kategorii.
2. Batch pre-fetch istniejących produktów po `product_uid`
   (`filter(product_uid__in=...)`).
3. `_prepare_product_create` / `_prepare_product_update` per item,
   `bulk_create` / `bulk_update`.
4. `_create_related_objects_for_products` — batch dla wariantów, szczegółów,
   zdjęć: pre-fetch po `str(variant_uid)` (⚠️ `variant_uid` to CharField — bez
   `str()` był bug z type-mismatch → `IntegrityError` przy ponownym imporcie),
   dedup zdjęć po zbiorze `(product_id, image_url)`, `bulk_create`.

`limit=1000` w URL, ale **serwer i tak zwraca max 500 pozycji na stronę**
(zaobserwowane). `page` rośnie tylko po sukcesie strony.

Item bez `creation_date` jest pomijany.

---

## 7. Krok INVENTORY

`_update_inventory_from_api` → pipeline (§5) → `_bulk_update_inventory(inventory_data)`
per strona (w kolejności).

`_bulk_update_inventory`:

1. Batch pre-fetch produktów (po `product_uid`) i wariantów (po
   `str(variant_uid)`, `select_related('product')`).
2. Dla każdego wariantu, którego stan się różni — **warunkowy UPDATE**:
   ```python
   changed = ProductVariant.objects.using('matterhorn1').filter(
       pk=variant.pk, stock=old_stock
   ).update(stock=new_stock, updated_at=timezone.now())
   ```
3. Wiersz `StockHistory` **tylko gdy UPDATE naprawdę zmienił rząd**
   (`changed == 1`), potem `bulk_create` historii (poza wspólną transakcją).

Dlaczego warunkowy UPDATE, a nie `bulk_update` + bezwarunkowa historia
(#230): decyzja "zapisz wiersz historii" oparta na `variant.stock != new_stock`
odczytanym poza transakcją była **niepodatna na wyścig** — nakładające się
runy (patrz §12) zapisywały tę samą zmianę wielokrotnie. `WHERE stock=old_stock`
serializuje pisarzy (łapie jeden run), a re-run widzi już nowy stan → 0 rzędów
→ brak wpisu (**idempotencja**).

Koszt: kilka warunkowych UPDATE-ów na run (tylko **faktycznie** zmienione
warianty — z logów 1–7 na stronę), nie N+1 na wszystkie.

`updated_at` ustawiane wprost, bo `MPD.tasks.update_stock_from_matterhorn1`
filtruje warianty po `updated_at`.

---

## 8. Wznawianie i checkpoint

- `_get_last_items_update_time()` — bierze `started_at` ostatniego udanego
  `ApiSyncLog` (status `success`/`partial`/`completed`), konwertuje na
  `Europe/Warsaw`, zwraca jako `last_update` do URL. **Brak poprzedniego
  udanego importu → `None` → import się nie zaczyna** (celowo, żeby nie
  ciągnąć całej historii).
- `_get_last_items_page()` — jeśli ostatni `ApiSyncLog` jest `error`/`running`/
  `interrupted`, ma `current_page > 1` i jest świeży (< 24 h) → wznów od tej
  strony. Wszystkie przerwane runy używają **tego samego** `last_update`
  (znacznik przeskakuje dopiero po `completed`), więc numer strony jest spójny.
- Po zapisaniu każdej strony ITEMS: `_update_items_import_status('running',
imported_count, next_page, ...)` — utrwala checkpoint.
- Import ITEMS, który padł na stronie N (5xx/sieć po wyczerpaniu prób), **nie**
  jest oznaczany `completed`. Kolejny tick celery-beat wznowi od strony N.
- Bug #214 (naprawiony): dawniej `page` rosło tylko po sukcesie, więc trwały
  5xx = nieskończona pętla do soft-timeoutu. Teraz strona po wyczerpaniu prób
  = twardy `status: error` + zachowany `current_page`.

INVENTORY **nie ma checkpointu** — zawsze zaczyna od strony 1
(`_bulk_update_inventory` per strona jest niezależny; bufor porządkujący jest
tam tylko dla przewidywalnej kolejności logów).

---

## 9. Harmonogram (celery-beat) i watchdog

Schedule w bazie (`django_celery_beat`, `DatabaseScheduler`), nie w kodzie:

| Zadanie                                         | Harmonogram                                        | Uwaga                                                                                                                                                            |
| ----------------------------------------------- | -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `matterhorn1.tasks.full_import_and_update`      | crontab `2,12,22,32,42,52 * * * *` (Europe/Warsaw) | co 10 min                                                                                                                                                        |
| `matterhorn1.tasks.watchdog_import_healthcheck` | co 5 min                                           | siatka bezpieczeństwa: `running` bez postępu > 15 min → `error`, bardzo stare (> 3 h) → `error`. Blokada = advisory lock, więc nie ma ghost-locków do sprzątania |
| `MPD.tasks.update_stock_from_matterhorn1`       | co 5 min                                           | most stanów matterhorn1 → MPD                                                                                                                                    |

Pozostałe taski (bez harmonogramu / punktowe):
`clean_old_stock_history` (kasuje wpisy `StockHistory` starsze niż N dni —
odpalane **ręcznie** z admina, widok „clean-history", domyślnie 90 dni),
`track_stock_changes` / `track_bulk_stock_changes` (kolejka `default`,
punktowy zapis do `StockHistory` poza importem), `sync_stock_changes_from_api`,
`get_import_status`, `test_periodic_task`.

**celery-beat po przestoju** (uśpienie hosta, restart) odpala **raz** każdy
pominięty cron job na starcie, potem wraca na normalny harmonogram — to
domyślne zachowanie, nie bug (widoczne w logach jako run o "dziwnej" minucie).

---

## 10. StockHistory i most do MPD

`StockHistory` — log zmian stanu (`variant_uid`, `product_uid`, `old_stock`,
`new_stock`, `stock_change`, `change_type` ∈ {`increase`,`decrease`,`no_change`},
`timestamp`). Zapisywany przez `_bulk_update_inventory` (§7) oraz
`stock_tracker.track_stock_change()` (punktowo).

Most do MPD: **`MPD.tasks.update_stock_from_matterhorn1`** (co 5 min):

1. Bierze warianty `matterhorn1` z `is_mapped=True` zmienione w oknie
   (`updated_at` w ostatnich ~15 min).
2. Po `mapped_variant_uid` znajduje wariant w MPD.
3. Aktualizuje `StockAndPrices` w MPD stanem z `matterhorn1`.

Dlatego `_bulk_update_inventory` ustawia `updated_at` jawnie — inaczej most by
pominął zmianę.

---

## 11. Admin

`src/apps/matterhorn1/admin.py`:

- `ProductAdmin` — lista, filtry (marka/kategoria — `make_scoped_filter`),
  akcje mapowania do MPD (`mpd_create` przez sagę, `assign_mapping`),
  podpowiedzi fuzzy.
- `StockHistoryAdmin` — read-only log. Po #229:
  - filtr `product_uid` przez **pole tekstowe** (`make_input_filter`), nie
    listę ~38 tys. wartości (to zabijało czas ładowania);
  - link do produktu z adnotacji `_product_pk` (jedno skorelowane podzapytanie,
    nie query per wiersz);
  - `show_full_result_count = False`;
  - dodatkowe widoki: bestsellery, popularne produkty, statystyki, czyszczenie
    historii.
- `ApiSyncLogAdmin`, `SagaAdmin`, `SagaStepAdmin` — read-only.

Wspólna baza: `core/wholesaler_admin/` (`RouterScopedQuerysetMixin`,
`ReadOnlyLogAdminMixin`, `StockHistoryAdminBase`, filtry).

---

## 12. Znane problemy i pułapki

| Problem                                             | Opis                                                                                                                                                                                                                      | Status                                                                                                                                                                                                                                                 |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Redeliver ubitych tasków / nakładające się runy** | Restart `celery-heavy` w połowie taska → Celery nie dostaje ACK → redeliveruje po czasie (do ~1 h) na przesuniętym `last_update`, równolegle z runem z beat. Powodowało duplikaty w `StockHistory` i "zawieszone" locki. | **Naprawione** (#238): `acks_late=False` (brak redeliveru) + advisory lock zamiast `cache.add` (brak ghost-locków, auto-release po padzie); `_fail_stale_running_imports` sprząta osierocone rekordy `running`. #230 dodatkowo utrzymuje idempotencję. |
| **Deploy nie jest automatyczny**                    | `deploy-vps.yml` nie odpala się po tagu (`GITHUB_TOKEN` nie triggeruje workflowów). Każdy deploy na prod jest w praktyce ręczny.                                                                                          | issue #224                                                                                                                                                                                                                                             |
| **Niezalogowane restocki**                          | Gdy między dwoma runami stan poszedł `0→N→0`, run widzi `0` i `0` → nic nie loguje. W `StockHistory` widać serię `1→0` "pod rząd" bez `0→1` między nimi (to nie duplikaty).                                               | drobne, nietknięte                                                                                                                                                                                                                                     |
| **`limit=1000` w URL, serwer daje 500**             | API tnie stronę do 500 pozycji niezależnie od `limit`. Kosmetyka.                                                                                                                                                         | —                                                                                                                                                                                                                                                      |
| **`.isdigit()` bez `str()`**                        | `variant_data.get('stock','0').isdigit()` w `_bulk_update_inventory` — pre-istniejący edge case (rzuci `AttributeError` gdy `stock` nie jest stringiem). Poza zakresem dotychczasowych fixów.                             | —                                                                                                                                                                                                                                                      |

Czyszczenie historycznych duplikatów: `python manage.py dedupe_stock_history`
(§14).

---

## 13. Testy

`src/apps/matterhorn1/tests/` (pytest-django, patrz [`../TESTING.md`](../TESTING.md)):

- `factories.py` — buildery ładunków API (`api_item`, `api_variant`,
  `inventory_record`).
- `mock_matterhorn.py` — mock B2BAPI (`responses`), stronicowanie +
  `transient_errors`.
- `conftest.py` — `no_sleep` (autouse — zeruje `time.sleep`), `matterhorn_api`,
  `mocked_responses`, `prior_items_sync`.
- Warstwy: `tests_unit_*` (helpery, pipeline, stock_tracker),
  `tests_integration_*` (saga, bulk import, admin, dedupe),
  `tests_e2e_import*` (pełny `full_import_and_update` z mockiem HTTP),
  `tests_performance_*` (`CaptureQueriesContext` — regresja liczby zapytań).
- `tests_import_resume.py` (w korzeniu appki) — wznawianie, soft-timeout.

Uruchomienie: `pytest src/apps/matterhorn1` (CI: `working-directory: src`,
`--cov=src/apps/matterhorn1 --cov-fail-under=53`).

---

## 14. Komendy zarządzania

`src/apps/matterhorn1/management/commands/`:

| Komenda                                                                                      | Rola                                                                          |
| -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `celery_import --action import` / `status`                                                   | ręczne odpalenie / status `full_import_and_update`                            |
| `dedupe_stock_history [--execute] [--window-minutes N]`                                      | czyści historyczne duplikaty `StockHistory` (dry-run domyślnie); idempotentna |
| `best_sellers`                                                                               | eksport CSV bestsellerów                                                      |
| `sync_products` / `sync_variants` / `sync_inventory` / `sync_brands_categories` / `sync_all` | starsze, punktowe importy (przed `full_import_and_update`)                    |
| `import_products_bulk` / `_optimized` / `_sequence`                                          | j.w.                                                                          |

---

## 15. Historia zmian (istotne PR-y)

| PR                    | Zmiana                                                                               |
| --------------------- | ------------------------------------------------------------------------------------ |
| #204                  | wznawianie importu ITEMS od przerwanej strony                                        |
| #210–#216, #219, #222 | migracja na pytest-django + pokrycie testami `matterhorn1` (98 → 213 testów)         |
| #217 (issue #214)     | trwały 5xx na stronie przerywa import zamiast pętlić do soft-timeoutu                |
| #222 (issue #221)     | `product_id` → `product_uid` w `views.py` (FieldError → 500)                         |
| #223                  | batch zapytań w imporcie ITEMS zamiast N+1                                           |
| #225                  | batch zapytań w `_bulk_update_inventory` (N+1)                                       |
| #226                  | pipeline pobierania stron ITEMS zamiast sekwencyjnego (wątek launcher, wczesny stop) |
| #227                  | odseparowanie wystrzeliwania stron od zapisu do bazy (osobny wątek)                  |
| #228                  | kontekst zadania Celery w logach z wątków (`???[???]` → `[<task_id>]`)               |
| #229                  | przyspieszenie changelist admina `StockHistory`                                      |
| #230                  | idempotentny `_bulk_update_inventory` (duplikaty w `StockHistory`)                   |
| #231                  | komenda `dedupe_stock_history`                                                       |

Powiązane: [`../HOW_IT_WORKS.md`](../HOW_IT_WORKS.md) §1 (import z hurtowni),
[`../PROJECT_OVERVIEW.md`](../PROJECT_OVERVIEW.md),
[`MATTERHORN_PERFORMANCE_OPTIMIZATION.md`](MATTERHORN_PERFORMANCE_OPTIMIZATION.md)
(indeksy w modelach).
