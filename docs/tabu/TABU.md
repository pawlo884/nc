# Tabu — dokumentacja aplikacji

Import katalogu i stanów magazynowych z hurtowni **Tabu**
(`b2b.tabu.com.pl/api/v1`, REST) do własnej bazy-lustra, skąd dane trafiają
do MPD i dalej do IdoSell.

Stan: 2026-09-06 (po domknięciu issue #233).
Referencje: [`apidocs.md`](apidocs.md) (API), [`database.md`](database.md) (baza/migracje).

## Spis

- [1. Przegląd](#1-przegląd)
- [2. Model danych](#2-model-danych)
- [3. Bazy i routing](#3-bazy-i-routing)
- [4. Komendy i endpointy](#4-komendy-i-endpointy)
- [5. Sync stanów — `sync_tabu_stock`](#5-sync-stanów--sync_tabu_stock)
- [6. Nowe produkty — `sync_tabu_new_products`](#6-nowe-produkty--sync_tabu_new_products)
- [7. Kategorie](#7-kategorie)
- [8. Saga → MPD](#8-saga--mpd)
- [9. Harmonogram (celery-beat)](#9-harmonogram-celery-beat)
- [10. StockHistory i most do MPD](#10-stockhistory-i-most-do-mpd)
- [11. Admin](#11-admin)
- [12. Różnice względem matterhorn1](#12-różnice-względem-matterhorn1)
- [13. Testy](#13-testy)

---

## 1. Przegląd

```
Tabu REST API ──(import)──▶ baza tabu ──(most stanów / mapowanie)──▶ MPD ──▶ eksport ──▶ IdoSell
  products/basic  (stany, ceny — flat lista wariantów)     MPD.tasks.update_stock_from_matterhorn1 (uwaga: nazwa
  products/{id}   (pełny produkt: opisy, gallery, warianty)   historyczna — obsługuje też tabu? NIE — patrz §10)
  products/categories
```

- **`products/basic`** — płaska lista **wariantów** (`id` = produkt, `variant_id` = wariant),
  pola: `store`, `price_net`, `price_gross`. Przyrostowo przez `update_from`.
- **`products/{id}`** — pełne dane produktu (opisy, `gallery`, `variants`, słowniki).
  Pobierane **pojedynczo** — używane przy wykrywaniu nowych produktów.
- **`products/categories`** — drzewo kategorii.
- Limit API: **100 requestów/minutę** (przy przekroczeniu blokada 2 min), max `limit=1000`.
- Uwierzytelnianie: nagłówek `X-API-KEY`. Konfiguracja: `TABU_API_BASE_URL`,
  `TABU_API_KEY` w `.env`.

Kod: `src/apps/tabu/`.

---

## 2. Model danych

`src/apps/tabu/models.py`. Wszystkie tabele z prefiksem `tabu_`.

| Model | Tabela | Rola | Klucz z API |
| --- | --- | --- | --- |
| `Brand` | `tabu_brand` | marka | `brand_id` = `str(producer_id)` (unique) |
| `Category` | `tabu_category` | kategoria + `path`, `parent` | `category_id` = `str(api_category_id)` (unique) |
| `TabuProduct` | `tabu_product_detail` | produkt, **`store_total`** (suma wariantów) | `api_id` (IntegerField, **unique**) |
| `TabuProductImage` | `tabu_product_gallery` | gallery, `unique(product, api_image_id)` | `api_image_id` |
| `TabuProductVariant` | `tabu_product_variant` | wariant, **`store`**, ceny | `api_id` (IntegerField, **unique**) |
| `ApiSyncLog` | `tabu_apisynclog` | log syncu (`sync_type`, `status`, `raw_response`) | — |
| `StockHistory` | `tabu_stock_history` | historia zmian stanu | — |
| `Saga` / `SagaStep` | `tabu_saga_logs` / `tabu_saga_steps` | saga mapowania do MPD | — |

Mapowanie do MPD: `TabuProduct.mapped_product_uid`, `TabuProductVariant.mapped_variant_uid`
/ `is_mapped`. Ustawiane ręcznie w adminie (`mpd_create` / `assign_mapping`,
wspólny `core/wholesaler_admin/`) albo po EAN.

**`store_total`** — suma `store` wszystkich wariantów produktu. Idzie do MPD przy
tworzeniu produktu z saga (`services.py`) i do raportów bestsellerów
(`bestsellers_data.py`), więc musi być poprawny (patrz §5 — liczony z sumy, nie
przyrostowo).

---

## 3. Bazy i routing

Router `core/db_routers.py` (`TabuRouter`) kieruje `app_label == 'tabu'` do
aliasu z `_get_tabu_db()`:

- **produkcja:** `tabu`
- **dev / testy:** `zzz_tabu`

W testach `DATABASE_ROUTERS = []`, `zzz_tabu` ma `TEST = {'MIRROR': 'default'}`.
Kod komend używa `router.db_for_write(TabuProduct)` → w testach zwraca `default`;
factory tworzą obiekty bez `.using()` → też `default`. Spójnie.

---

## 4. Komendy i endpointy

Taski Celery (`tabu/tasks.py`) to cienkie wrappery wokół management commands
(`tabu/management/commands/`):

| Task | Komenda | Endpoint | Częstość |
| --- | --- | --- | --- |
| `sync_tabu_stock` | `sync_tabu_stock` | `products/basic` | co 10 min |
| `sync_tabu_products_update` | `sync_tabu_new_products` | `products/{id}` | co 240 min |
| `sync_tabu_categories` | `sync_tabu_categories` | `products/categories` | co 7 dni |
| `watchdog_tabu_stock_lock` | — (no-op) | — | co 5 min |

Pozostałe komendy: `sync_tabu_products` (pełny import po ID),
`import_tabu_by_id`, `find_common_eans`, `check_tabu_mpd_db`, `clear_tabu_data`,
`tabu_best_sellers`, `test_tabu_connection`, `setup_tabu_*_task` (rejestracja
PeriodicTask).

`make_api_request` (w `base_tabu_api_command`): retry x3, przy `429` czeka 120 s.

---

## 5. Sync stanów — `sync_tabu_stock`

`tabu.tasks.sync_tabu_stock` (co 10 min):

1. **Advisory lock** `advisory_lock('tabu:sync_tabu_stock')` (`core.pg_locks`).
   Nie zdobyty → `{'status': 'skipped', 'reason': 'already_running'}`. Lock
   zwalnia się sam gdy połączenie workera padnie — **bez TTL, bez watchdoga,
   bez ryzyka zawieszonego locka** (patrz §12).
2. `update_from` = `started_at` ostatniego `ApiSyncLog` ze **statusem
   `completed`** (`stock_update`/`stock_full`); brak → 24 h wstecz. Po
   nieudanym runie okno cofa się do ostatniego udanego (catch-up).
3. `call_command('sync_tabu_stock', '--update-from', update_from)`.
4. Błąd → `self.retry` (max 3, co 120 s).

Komenda `sync_tabu_stock`:

1. Stronicowane `GET products/basic?update_from=…` → płaska lista rekordów.
2. **Wczesny stop:** jeśli odcisk (`sha1` z posortowanych `(variant_id, store,
   price_net, price_gross)`) == odcisk z poprzedniego zakończonego runu →
   pomiń cały run (`skipped_reason: identical_fetch_as_previous_run`). To nie
   „ta sama liczba rekordów" — porównanie **danych** (poprawka #233).
3. **`_apply_stock_updates(records)` — batch, bez N+1:**
   - **1 `SELECT`** wariantów po `api_id__in` (`select_related('product')`);
   - **warunkowy `UPDATE` per zmieniony wariant** —
     `filter(pk=v.pk, store=old_store).update(store=new, price…)`. Wiersz
     `StockHistory` **tylko gdy `UPDATE` zmienił rząd** → idempotencja (re-run
     widzi już nowy stan) + brak wyścigu (redeliver/nakładający się run nie
     powiela historii);
   - ceny wariantów bez zmiany stanu → jeden `bulk_update`;
   - **`store_total` = SUMA wariantów** produktu (agregat `Sum` + `bulk_update`),
     nie przyrostowo → koniec dryfu (poprawka #233);
   - historia → `bulk_create`.

Liczba zapytań skaluje się ze **zmienionymi** wariantami (garstka przy
`update_from`), nie z liczbą w danych. Przed poprawką: `BEGIN` + `SELECT` +
`variant.save` + `product.save` + `INSERT` + `COMMIT` **na każdy rekord**.

INVENTORY (stany) nie ma checkpointu — zawsze przetwarza całą pobraną paczkę.

---

## 6. Nowe produkty — `sync_tabu_new_products`

`tabu.tasks.sync_tabu_products_update` (co 240 min):

Persistentny licznik `check_range` w `ApiSyncLog.raw_response`:

- każdy run sprawdza o 1 ID więcej niż poprzedni (`check_range += 1`), od `max(api_id)+1`;
- `GET products/{id}` — `404` = brak, `200` = **`_save_product`** (produkt +
  gallery + warianty przez mappery `map_api_product_to_model` /
  `map_api_variant_to_model`, `update_or_create`), potem sprawdza kolejne ID aż
  do `404`;
- znaleziono cokolwiek → `check_range = 0` (reset), następny run zaczyna od 1;
- dodatkowo re-sprawdza wcześniejsze `404` (API bywa opóźnione).

Przykład: run z `check_range=3` sprawdza `max+1 .. max+3`; jak trafi na `200` —
importuje i idzie dalej, reset.

---

## 7. Kategorie

`sync_tabu_categories` (co 7 dni) — `GET products/categories`, `update_or_create`
po `category_id`, buduje `parent` i `path`.

---

## 8. Saga → MPD

`tabu/services.py` — `create_mpd_product_from_tabu` / `create_mpd_variants_from_tabu`
/ `upload_tabu_images_to_mpd`, przez `core.saga` (`BaseSagaOrchestrator`,
kompensacja w odwrotnej kolejności, log do `tabu_saga_logs`/`tabu_saga_steps`).
Wołane z akcji admina (`mpd_create` / `assign_mapping`).

`producer_color` na wariancie/zdjęciu MPD ustawiany z nazwy koloru wariantu
Tabu (mapowanie per kolor hurtowni, v1.41).

---

## 9. Harmonogram (celery-beat)

Schedule w bazie (`django_celery_beat`, `DatabaseScheduler`):

| Zadanie | Częstość |
| --- | --- |
| `tabu.tasks.sync_tabu_stock` | co 10 min |
| `tabu.tasks.sync_tabu_products_update` | co 240 min |
| `tabu.tasks.sync_tabu_categories` | co 7 dni |
| `tabu.tasks.watchdog_tabu_stock_lock` | co 5 min (no-op — advisory lock nie wymaga watchdoga) |

Wszystkie taski działają na kolejce `default` (worker `celery-default`).

---

## 10. StockHistory i most do MPD

`StockHistory` (`tabu_stock_history`): `variant_api_id`, `product_api_id`,
`old_stock`, `new_stock`, `stock_change`, `change_type`, `timestamp`. Zapisywany
przez `_apply_stock_updates` (bulk_create) — `tabu.stock_tracker.track_stock_change`
istnieje (tested), ale nie jest już wołany przez sync.

Most do MPD: **`MPD.tasks.update_stock_from_matterhorn1`** — nazwa historyczna,
ale obsługuje **wszystkie** hurtownie po `mapped_variant_uid` (bierze warianty
z `is_mapped=True` zmienione w oknie po `updated_at`). Dlatego
`_apply_stock_updates` ustawia `updated_at` wariantu przez warunkowy `UPDATE`.

---

## 11. Admin

`src/apps/tabu/admin.py`:

- `TabuProductAdmin` — lista, filtry `TabuBrandFilter`/`TabuCategoryFilter`
  (scoped), `last_update`; akcje mapowania do MPD.
- `TabuProductVariantAdmin`, `TabuProductImageAdmin`, `BrandAdmin`, `CategoryAdmin`.
- `StockHistoryAdmin` (`ReadOnlyLogAdminMixin`) — prosty: `list_filter =
  ['change_type', 'timestamp']`. **Brak** buga z filtrem dużej kardynalności /
  N+1 w linku (który dotknął matterhorn1 — #229).
- `ApiSyncLogAdmin`, `SagaAdmin`, `SagaStepAdmin` — read-only.

---

## 12. Różnice względem matterhorn1

| | matterhorn1 | tabu |
| --- | --- | --- |
| Blokada importu | Redis `cache.add` (TTL 1 h) — **ryzyko zawieszonego locka** po padzie workera (issue #238) | **PostgreSQL advisory lock** — auto-release, bez TTL, bez watchdoga |
| Idempotencja stanów | warunkowy `UPDATE` (#230) | warunkowy `UPDATE` (analogicznie) |
| `store_total` / `stock_total` | `@property` (suma na żądanie) | pole liczone z sumy przy syncu |
| Pipeline pobierania stron | współbieżny (wątek launcher, #226/#227) | sekwencyjny (`products/basic` szybkie, mniejszy wolumen) |
| Checkpoint/wznawianie ITEMS | tak (`current_page`) | nie ma (nowe produkty przez `check_range`) |
| Admin StockHistory | wymagał optymalizacji (#229) | od początku prosty |

**Wzorzec advisory lock z tabu jest rekomendowany dla matterhorn1** (issue #238).

---

## 13. Testy

`src/apps/tabu/tests/` (pytest-django, jak `matterhorn1/tests/`):

- `factories.py` — `tabu_product`, `tabu_variant`, `basic_record`,
  `api_product_detail`, `api_variant_detail`.
- `mock_tabu.py` — `mock_products_basic`, `mock_product_detail` (`responses`).
- `conftest.py` — `no_sleep` (autouse), `tabu_api`, `mocked_responses`.
- Pliki: `tests_unit_stock_tracker`, `tests_integration_sync_stock`
  (`_apply_stock_updates` + `call_command`), `tests_integration_tasks`
  (4 taski Celery + advisory lock), `tests_integration_new_products`
  (`check_range`), `tests_integration_save_product` (`_save_product`).
- Starsze (w korzeniu appki): `tests_models`, `tests_saga`, `tests_serializers`,
  `tests_pg_locks`.

CI: `pytest --cov=src/apps/tabu ... --cov-fail-under=53` (wspólnie z matterhorn1;
`management/commands/*` poza pomiarem — `omit` w `pyproject.toml`).

Historia zmian: #234 (infra), #235 (`_should_skip_processing`), #236 (batch +
`store_total`), #237 (testy tasków/nowych produktów), #240 (`update_from`
status filter), #241 (`_save_product` + CI). Tracking: issue #233.
