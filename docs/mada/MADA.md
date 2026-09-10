# Mada — dokumentacja aplikacji

Import katalogu i stanów magazynowych z hurtowni **Mada** (feed XML pod
`get_xml.php`) do własnej bazy-lustra, skąd dane trafiają do MPD i dalej do
IdoSell / PrestaShop.

Stan: 2026-09-06 (issue #243 — idempotencja stanów, N+1, pokrycie testami).
Sąsiednie dokumenty: [`matterhorn/MATTERHORN1.md`](../matterhorn/MATTERHORN1.md),
[`tabu/TABU.md`](../tabu/TABU.md), [`../SAGA_PATTERN_README.md`](../SAGA_PATTERN_README.md).

## Spis

- [1. Przegląd](#1-przegląd)
- [2. Feed XML i API](#2-feed-xml-i-api)
- [3. Model danych](#3-model-danych)
- [4. Bazy i routing](#4-bazy-i-routing)
- [5. Komendy](#5-komendy)
- [6. Import pełny — `sync_mada_full`](#6-import-pełny--sync_mada_full)
- [7. Import przyrostowy — `sync_mada_partial`](#7-import-przyrostowy--sync_mada_partial)
- [8. Importer — upsert i idempotencja stanów](#8-importer--upsert-i-idempotencja-stanów)
- [9. Saga → MPD](#9-saga--mpd)
- [10. Most stanów do MPD](#10-most-stanów-do-mpd)
- [11. Harmonogram (celery-beat)](#11-harmonogram-celery-beat)
- [12. Admin](#12-admin)
- [13. Różnice względem matterhorn1 / tabu](#13-różnice-względem-matterhorn1--tabu)
- [14. Testy](#14-testy)

---

## 1. Przegląd

```
Mada feed XML ──(import)──▶ baza mada ──(adapter źródłowy / saga)──▶ MPD ──▶ eksport ──▶ IdoSell / PrestaShop
  get_xml.php (manifest)          MadaProduct / MadaProductVariant       MadaAdapter czyta .stock po EAN
  get_xml.php?file=… (ZIP)        StockHistory (audyt zmian stanu)       (model pull, nie push)
```

- **`full`** — pełny katalog (~24 MB `products.xml`), generowany raz dziennie
  (~00:01). Źródło prawdy; produkty nieobecne w pliku → `is_active=False`.
- **`partial`** — przyrostowe pliki generowane ~co 10 min (tylko zmienione
  produkty). Optymalizacja świeżości między pełnymi importami.

Feed nie ma tokenów uwierzytelniających w nagłówkach — login (`l`) i hasło
(`p`) idą w query stringu (patrz §2).

## 2. Feed XML i API

`MadaApiClient` (`mada/api_client.py`), `base_url = MADA_API_BASE_URL`,
auth = `MADA_API_LOGIN` / `MADA_API_PASSWORD`.

| Wywołanie                      | Zwraca                                                                            |
| ------------------------------ | --------------------------------------------------------------------------------- |
| `GET get_xml.php` (bez `file`) | manifest: `<FILES><FILE><NAME/><DATE/><TYPE>full\|partial</TYPE></FILE>…</FILES>` |
| `GET get_xml.php?file=<NAME>`  | ZIP zawierający `products.xml`                                                    |

Metody klienta:

- `list_files()` → `List[MadaFeedFile]` (name, date, type); niepoprawna data → `None`, wpis zostaje.
- `latest_full_file()` → najnowszy `TYPE=full` wg daty, albo `None`.
- `partial_files_after(after_name)` → pliki `partial` o nazwie leksykalnie większej
  niż `after_name` (nazwy `YYYY-MM-DD_HHMMSS` → porównanie leksykalne = chronologiczne), rosnąco.
- `download_products_xml(file_name)` → `bytes` zawartości `products.xml` (rozpakowany ZIP).

**Redakcja danych logowania:** wyjątki `requests`/`urllib3` wpisują pełny URL
(z hasłem) w `str()`. `_redact_credentials` zamienia `?l=…` / `&p=…` na `***`
przed przekazaniem do `MadaApiError` / logów / Sentry.

**Parser** (`mada/parser.py`) — `products.xml` parsowany strumieniowo
(`ET.iterparse` + `elem.clear()` po każdym `<PRODUCT>`), bo plik pełny nie
mieści się wygodnie w DOM:

- `parse_producers(xml)` → `{producer_id: name}` z jednego bloku `<PRODUCERS>` na początku pliku.
- `iter_products(xml)` → generator dictów; `<PRODUCT>` bez numerycznego `<ID>` jest pomijany,
  błąd parsowania pojedynczego elementu → log + `continue` (nie przerywa importu).

## 3. Model danych

Baza `mada` (`db_table` bez prefiksu app; patrz `mada/models.py`).

| Model                | Klucz                            | Uwagi                                                                                                                                |
| -------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `Brand`              | `producer_id` (unique)           | z `<PRODUCERS>`                                                                                                                      |
| `Category`           | `category_id` (unique)           | `c1-c2` z `<CATEGORY>`; self-FK `parent` (drzewo `c1` → `c1-c2`)                                                                     |
| `MadaProduct`        | `api_id` (unique)                | `<ID>`; `is_active`, `mapped_product_uid`, `raw_data` (JSON: attributes, similar, producer info)                                     |
| `MadaProductImage`   | `(product, api_image_id)` unique | `<IMG id>` + URL + `order`                                                                                                           |
| `MadaProductVariant` | `(product, variant_key)` unique  | **`variant_key` = EAN gdy jest, inaczej `"color\|size"`** — feed nie nadaje wariantom id; `stock`, `mapped_variant_uid`, `is_mapped` |
| `ApiSyncLog`         | —                                | `sync_type` = `full_import` / `partial_import`; `status`, `file_name`, liczniki                                                      |
| `StockHistory`       | —                                | audyt zmian stanu: `product_api_id`, `variant_key`, `old/new_stock`, `change_type`                                                   |
| `Saga` / `SagaStep`  | —                                | log kroków saga Mada↔MPD (`core.saga_models`)                                                                                        |

Cena jest **na produkcie** (`MadaProduct.price`), nie na wariancie — inaczej niż tabu/matterhorn1.

## 4. Bazy i routing

- Produkcja: osobna baza `mada`; DEV: `zzz_mada`. Router `MadaRouter`
  (`core.db_routers`) kieruje modele `mada` + lazy-wybór prefiksu.
- Komendy importu używają `router.db_for_write(MadaProduct)` — działa też w testach
  (routery wyłączone → `default`).
- **Uwaga:** `cleanup_orphaned_mada_mapping` sięga `_get_mada_db()` / `_get_mpd_db()`
  bezpośrednio (poza remapowaniem testowym) — nie jest pokryte testami integracyjnymi.

## 5. Komendy

| Komenda                                                                                              | Rola                                                                                         |
| ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `sync_mada_full [--file=<NAZWA>]`                                                                    | pełny import (§6)                                                                            |
| `sync_mada_partial`                                                                                  | import przyrostowy po kursorze (§7)                                                          |
| `cleanup_empty_mada_products [--dry-run]`                                                            | usuwa produkty bez `NAME` w feedzie i bez `mapped_product_uid` (CASCADE na warianty/zdjęcia) |
| `cleanup_orphaned_mada_mapping [--dry-run]`                                                          | zeruje `mapped_*_uid` wskazujące na nieistniejące już rekordy MPD                            |
| `clear_mada_data`                                                                                    | czyści bazę-lustro mada                                                                      |
| `setup_mada_sync_task [--partial-interval N] [--full-hour H --full-minute M] [--disable] [--delete]` | rejestruje periodic tasks                                                                    |
| `setup_mada_cleanup_task`                                                                            | rejestruje `cleanup_empty_products`                                                          |
| `test_mada_connection`                                                                               | sanity-check połączenia z feedem                                                             |

## 6. Import pełny — `sync_mada_full`

1. `--file` albo `client.latest_full_file()` → `file_name`; `ApiSyncLog(status='running')`.
2. `download_products_xml` → `parse_producers` → `sync_brands` (bulk upsert marek).
3. `brand_cache = load_brand_cache(db)` — marki raz do dicta (bez SELECT-a per produkt).
4. `iter_products` w partiach po `BATCH_SIZE = 200`; każdy produkt w **osobnym
   `transaction.atomic` (savepoint)** — błąd jednego nie psuje reszty batcha
   (na Postgresie błąd w `atomic()` unieważnia całą otaczającą transakcję).
5. Po przejściu całego pliku: `MadaProduct.exclude(api_id__in=seen).filter(is_active=True).update(is_active=False)`
   — wygaszenie produktów nieobecnych w feedzie.
6. `ApiSyncLog(status='completed')` + liczniki (`processed` / `created` / `updated` / `failed`).

Błąd pobrania pliku / parsowania → `ApiSyncLog(status='failed')` + `CommandError`.

## 7. Import przyrostowy — `sync_mada_partial`

- **Kursor** = najwyższy `file_name` wśród `ApiSyncLog(sync_type='partial_import', status='completed')`.
- `client.partial_files_after(kursor)` → wszystkie nowsze pliki, po kolei.
- Każdy plik: własny `ApiSyncLog`, `sync_brands` + `load_brand_cache`, pętla
  `iter_products` z per-produktowym `atomic`.
- **Ograniczenie znane:** jeśli plik partial zawiedzie, a kolejny się powiedzie,
  kursor przeskakuje nieudane okno — nadrobi je dopiero najbliższy `sync_mada_full`
  (źródło prawdy). Świadoma decyzja, nie bug.

## 8. Importer — upsert i idempotencja stanów

`mada/importer.py`:

- `sync_brands(db, producers)` — `bulk_create(ignore_conflicts=True)` + `bulk_update`.
- `resolve_category(db, categories, cache)` — `get_or_create` kategorii `c1` i `c1-c2`;
  `category_cache` żyje w obrębie **jednego** przebiegu (nie globalnie).
- `upsert_product(db, pd, cat_cache, brand_cache=None)` — `update_or_create` po `api_id`;
  marka z `brand_cache` (gdy podany) zamiast `Brand.filter().first()` per produkt.
- `upsert_variants(db, product, variants)` — **kluczowa ścieżka stanów:**

  ```python
  if current.stock != v['stock']:
      n = (MadaProductVariant.objects.using(db)
           .filter(pk=current.pk, stock=old_stock)          # warunkowy UPDATE
           .update(stock=new_stock, updated_at=timezone.now()))
      if n:                                                  # tylko gdy wiersz faktycznie zmieniony
          history_rows.append(build_stock_history_row(...))
  ...
  StockHistory.objects.using(db).bulk_create(history_rows)   # jeden INSERT, nie per wariant
  ```

  - **race-safe** — `WHERE stock=old` serializuje równoległych zapisujących
    (`sync_mada_full` i `sync_mada_partial` mają **osobne** advisory locki i mogą
    lecieć jednocześnie);
  - **idempotentne** — powtórny import tego samego okna (redelivery Celery po
    `visibility_timeout=3600` przy `task_acks_late=True`) widzi stan docelowy →
    `0` wierszy → brak duplikatu w `StockHistory`.

  To ten sam wzorzec co matterhorn1 (#230) i tabu (#236).

- `upsert_images(db, product, images)` — `bulk_create(ignore_conflicts=True)` + kasowanie nieobecnych.
- `build_stock_history_row(...)` (w `stock_tracker.py`) — niezapisany `StockHistory` do `bulk_create`;
  `track_stock_change(...)` zostaje jako wrapper do użycia ad-hoc (shell / saga).

## 9. Saga → MPD

`mada/services.py` + `mada/saga.py` (`MadaSagaOrchestrator` na `core.saga`).
Wywoływane z admina (`mpd_create` / `assign_mapping`).

Kroki: **(1)** utworzenie produktu + wariantów w MPD, **(2)** zapis mapowania
(`mapped_product_uid` / `mapped_variant_uid`) w Mada. Błąd kroku 2 → kompensacja
usuwa produkt z MPD (`merge_result_into_own_step_data = True` przekazuje
`mpd_product_id` z execute do compensate).

Różnice modelu Mada w sadze:

- wariant nie ma numerycznego id → do `ProductVariantsSources.variant_uid`
  (integer w MPD) nic nie trafia, klucz to `variant_key`;
- cena z `MadaProduct.price` (nie z wariantu);
- brak kodu producenta w feedzie — tylko z formularza;
- zdjęcia wyłącznie z `product.images` (brak głównego `image_url` na produkcie).

## 10. Most stanów do MPD

**Model pull, nie push.** Nie ma taska „wypchnij stany Mada do MPD".
`MPD/source_adapters/mada.py::MadaAdapter` czyta `MadaProductVariant.stock`
**na żywo po EAN** (`get_variants_by_eans`, `get_all_variants_for_product`,
`get_unmapped_variants_for_mpd_product`) podczas linkowania / eksportu MPD.

`mada.StockHistory` jest **tylko audytem** — nic z niego nie odczytuje MPD
(inaczej niż `MPD.tasks.update_stock_from_matterhorn1` dla matterhorn1).

Sprzątanie mapowań: `MPD/signals.py` (`post_delete` na `Products`) zeruje
`mapped_product_uid` / `mapped_variant_uid` w Mada; historyczne sieroty czyści
`cleanup_orphaned_mada_mapping`.

## 11. Harmonogram (celery-beat)

`mada/tasks.py` — cienkie wrappery na komendy, każdy z advisory lockiem:

| Task                                     | Lock                          | Domyślny cykl (`setup_mada_sync_task`) |
| ---------------------------------------- | ----------------------------- | -------------------------------------- |
| `mada.tasks.sync_mada_full`              | `mada:sync_mada_full`         | codziennie 00:15                       |
| `mada.tasks.sync_mada_partial`           | `mada:sync_mada_partial`      | co 15 min                              |
| `mada.tasks.cleanup_empty_products`      | `mada:cleanup_empty_products` | dziennie (osobny setup)                |
| `mada.tasks.watchdog_import_healthcheck` | —                             | co 5 min (migracja `0002`)             |

Lock nie zdobyty → `{'status': 'skipped', 'reason': 'already_running'}`.
Błąd komendy → `self.retry`.

**Uwaga:** full i partial mają **różne** nazwy locka — mogą lecieć równolegle.

**Sprzątanie osieroconych `running` (#267):** jeśli worker padnie w trakcie
(SIGKILL, hard time limit Celery) zanim komenda dojdzie do `except`/`finally`,
`ApiSyncLog` zostaje w `status='running'` na zawsze — advisory lock zwalnia się
sam (koniec sesji DB), ale log nie. Dwie warstwy sprzątania, jak w matterhorn1
(#238):

- **samoleczenie** — `sync_mada_full`/`sync_mada_partial`, zaraz po zdobyciu
  locka, oznaczają jako `failed` każdy istniejący `running` tego samego
  `sync_type` (skoro mamy wyłączny lock, to na pewno sierota);
- **watchdog** (`watchdog_import_healthcheck`, co 5 min) — backstop gdyby
  kolejny przebieg się nie odpalił: `running` starszy niż 60 min (partial) /
  180 min (full) → `failed`.

**Routing kolejki:** `sync_mada_full` idzie na `celery-heavy`
(`CELERY_TASK_ROUTES`, #263/#265) — długi task nie może blokować 3 slotów
`celery-fast` zarezerwowanych pod 5-minutowe krytyczne taski. `PeriodicTask`
(`setup_mada_sync_task`) **musi** mieć `queue=None`, inaczej jawny `queue` w
`apply_async` wygrywa z `CELERY_TASK_ROUTES` i task ucieka na złego workera.
Bezpieczeństwo stanów zapewnia idempotentny `upsert_variants` (§8), nie lock.
Ewentualne ujednolicenie locka → osobna decyzja (#243).

## 12. Admin

`mada/admin.py` — `RouterScopedQuerysetMixin` + `db_alias_getter = _get_mada_db`
(scoping zapytań do bazy mada).

- `MadaProductAdmin` — `get_queryset` z `select_related('brand', 'category')` +
  `Subquery` na pierwsze zdjęcie (miniatura bez N+1); filtry `make_scoped_filter`
  (Marka ↔ Kategoria); `change_view` dokłada kontekst MPD (sugestie fuzzy, kolory
  źródłowe) i endpointy `mpd-create` / `assign-mapping`.
- `ApiSyncLogAdmin`, `StockHistoryAdmin`, `SagaAdmin`, `SagaStepAdmin` —
  `ReadOnlyLogAdminMixin`.
- Inline: warianty + zdjęcia (z podglądem miniatury, `fallback_host='mada.pl'`).

## 13. Różnice względem matterhorn1 / tabu

| Aspekt             | Mada                                            | matterhorn1 / tabu                                        |
| ------------------ | ----------------------------------------------- | --------------------------------------------------------- |
| Transport          | feed XML w ZIP (manifest + pliki)               | REST JSON                                                 |
| Auth               | login/hasło w query stringu (redakcja w logach) | token w nagłówku                                          |
| Id wariantu        | brak — `variant_key` = EAN \| `"color\|size"`   | numeryczne `variant_uid` / `api_id`                       |
| Cena               | na produkcie                                    | na wariancie                                              |
| Przyrostowość      | kursor po `file_name` plików partial            | `update_from` / `last_update` z `ApiSyncLog`              |
| Wygaszanie         | `is_active=False` dla nieobecnych w `full`      | brak / miękkie                                            |
| Most stanów do MPD | pull przez `MadaAdapter` (na żywo)              | push (`update_stock_from_matterhorn1`) + adapter          |
| Lock importu       | pg advisory lock, **osobny full vs partial**    | matterhorn1: Redis `cache.add`; tabu: pg advisory (jeden) |

Wspólne: idempotentny warunkowy UPDATE stanów + `bulk_create` historii,
wzorzec saga `core.saga`, `ApiSyncLog`, `StockHistory`.

## 14. Testy

`src/apps/mada/tests/` (pakiet, pytest) + starsze płaskie `tests_*.py`
(`django.test.TestCase`):

| Plik                                                                          | Zakres                                                                                                            |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `tests/factories.py`                                                          | buildery DB (`brand`, `category`, `mada_product`, `mada_variant`) + dictów feedu (`product_dict`, `variant_dict`) |
| `tests/mock_mada.py`                                                          | buildery manifestu / `products.xml` / ZIP dla `responses`                                                         |
| `tests/tests_unit_api_client.py`                                              | manifest, wybór full/partial, ZIP, redakcja hasła                                                                 |
| `tests/tests_integration_tasks.py`                                            | advisory lock (skip), retry, regresja: osobne locki full vs partial                                               |
| `tests/tests_integration_sync_full.py`                                        | import + log, wygaszanie nieobecnych, izolacja błędu produktu, `--file`, idempotencja                             |
| `tests/tests_integration_sync_partial.py`                                     | kursor plików, no-op, brak duplikatów przy redelivery                                                             |
| `tests/tests_integration_importer_idempotent.py`                              | warunkowy UPDATE, brak duplikatów historii, zmiana atrybutu bez wpisu                                             |
| `tests/tests_performance_importer.py`                                         | `brand_cache` = 0 SELECT-ów `mada_brand` w pętli, historia jednym INSERT                                          |
| `tests/tests_integration_cleanup_commands.py`                                 | `cleanup_empty_mada_products`                                                                                     |
| `tests_importer.py` / `tests_parser.py` / `tests_models.py` / `tests_saga.py` | logika importu, parser, modele, saga Mada↔MPD                                                                     |

CI (`check-branch.yml`): `--cov=src/apps/mada` w puli progu `--cov-fail-under`
(management/commands poza pomiarem wg `[tool.coverage.run] omit`).
Uruchomienie: `pytest src/apps/mada`.
