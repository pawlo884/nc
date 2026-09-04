# Testy — plan i konwencje

Punkt startowy: **kompleksowe pokrycie `matterhorn1`** (unit + integration + e2e),
przy okazji migracja całego projektu na `pytest-django`.

Tracking: #208. Stan wyjściowy matterhorn1: ~98 testów w 7 plikach
`tests*.py` — dobrze pokryte modele / serializery / REST API, **niepokryte**:
`tasks.py` (pipeline importu, 1850 LOC), `saga.py` (główna saga produktu),
`admin.py` (mpd_create / assign_mapping / auto_map), `views*.py`,
`stock_tracker.py`, komendy `sync_*`.

## Decyzje

| Temat            | Ustalenie                                                                                                                                                                                     |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Istniejące testy | **Zachować** — pytest uruchamia `unittest.TestCase` natywnie; reorganizacja w warstwy, nie przepisywanie                                                                                      |
| „e2e"            | **Pełny pipeline importu z zamockowanym HTTP** (`responses`): `full_import_and_update` od API → asercje stanu w matterhorn1 + MPD, z sagą i linkowaniem po EAN. Deterministyczne, działa w CI |
| Runner           | **Migracja na `pytest-django`** + `responses` + `pytest-cov`                                                                                                                                  |

---

## Faza 0 — migracja na pytest-django (infra) ✅

Bez nowych testów logiki — przełączenie runnera tak, żeby istniejące ~98
testów przechodziło 1:1.

- [x] `requirements.ci.txt`: `pytest`, `pytest-django`, `pytest-cov`, `coverage`, `responses`
- [x] `pyproject.toml` → `[tool.pytest.ini_options]`:
  - `DJANGO_SETTINGS_MODULE = "core.settings.dev"`
  - `python_files = ["tests*.py"]` — **tylko** `tests*.py`, żeby nie zbierać
    `management/commands/test_*_connection.py` (jak stary `--pattern`)
  - `testpaths = ["src/apps"]`, `pythonpath = ["src/apps", "src"]`
  - `addopts = "--reuse-db --strict-markers -ra"`
  - markery: `unit`, `integration`, `e2e`
- [x] **`core/settings/dev.py`**: `if 'test' in sys.argv` (2 miejsca) → wspólny flag
  ```python
  RUNNING_TESTS = 'test' in sys.argv or 'pytest' in sys.modules
  ```
  Inaczej pod pytest nie zadziała: wyłączony routing baz, `DummyCache`,
  wyłączony throttling, `CELERY_TASK_ALWAYS_EAGER`.
- [x] **usunięty pusty `src/apps/__init__.py`** — z nim pytest importował moduły
      jako `apps.matterhorn1.*` (≠ `matterhorn1` z `INSTALLED_APPS`) i wywalał
      `RuntimeError: Model ... doesn't declare an explicit app_label`. Bez niego
      `matterhorn1` jest top-level (jak w `manage.py`, gdzie `src/apps` jest w `sys.path`).
- [x] `conftest.py` (root): fixture'y `api_client`, `admin_user`, `auth_client`, `all_dbs`
- [x] `.github/workflows/check-branch.yml`: krok „Testy Django" → `pytest --cov=src/apps`
- [ ] pozostałe docs (`HOW_TO_FIX_TESTS.md`, `DJANGO_6_COMPATIBILITY.md` …) — komenda `manage.py test` → `pytest` (osobno)
- [x] weryfikacja: `pytest src/apps/matterhorn1` = 98 pass (tyle samo co `manage.py test`)

> Uwaga o bazach: `dev.py` w trybie testów wyłącza routery (`DATABASE_ROUTERS = []`)
> — wszystkie modele idą do `default`, pozostałe bazy to `MIRROR: default`.
> Wywołania `.using('MPD')` w kodzie nadal działają (alias → ta sama baza testowa).
> Klasy testów cross-DB deklarują `databases = {'default', 'MPD', ...}` (TestCase)
> lub `@pytest.mark.django_db(databases=conftest.ALL_DATABASES)` (pytest-style).

### Uruchamianie

```bash
pip install -r src/requirements.ci.txt        # pytest + wtyczki

pytest                                         # wszystko
pytest src/apps/matterhorn1                     # jedna apka
pytest src/apps/matterhorn1/tests_saga.py -q    # jeden plik
pytest -m "not e2e"                             # szybki cykl
pytest -k "saga and compensat"                  # po nazwie
pytest --cov=src/apps --cov-report=term-missing # z pokryciem
```

`--reuse-db` trzyma testową bazę między uruchomieniami (pierwszy raz wolno,
kolejne szybko). `--create-db` wymusza odtworzenie po zmianie migracji.

---

## Warstwy testów matterhorn1

### Unit (izolowane, bez DB gdy się da)

| Cel                                                                            | Moduł                           |
| ------------------------------------------------------------------------------ | ------------------------------- |
| `_parse_creation_date`, parsowanie pól API, mapowanie item→model               | `tasks.py` (helpery)            |
| `_prepare_product_create` / `_prepare_product_update` — budowa obiektu z itemu | `tasks.py`                      |
| normalizacja EAN / kodów, fallback SKU                                         | `defs_db.py`, `source_adapters` |
| `stock_tracker` — wykrywanie zmiany stanu, próg, brak zmiany                   | `stock_tracker.py`              |
| `transaction_logger` — format wpisu, fail-open                                 | `transaction_logger.py`         |
| `database_utils` — buildery zapytań / bulk helpers                             | `database_utils.py`             |
| serializery walidacja (uzupełnić braki)                                        | `serializers.py`                |

### Integration (z DB, komponenty razem)

| Cel                                                                            | Zakres                                |
| ------------------------------------------------------------------------------ | ------------------------------------- |
| `SagaOrchestrator` + `SagaService.create_product_with_mapping` — happy path    | `saga.py`                             |
| **kompensacja**: krok 2 rzuca → krok 1 cofnięty, brak sieroty w MPD            | `saga.py`                             |
| logowanie sagi fail-open (błąd zapisu logu nie przerywa sagi)                  | `core/saga.py` + `saga.py`            |
| admin `mpd_create` — POST formularza → produkt w MPD + mapping w matterhorn1   | `admin.py`                            |
| admin `assign_mapping` — podpięcie istniejącego produktu MPD                   | `admin.py`                            |
| admin `auto_map` / akcja linkowania → dispatch taska (jest 1 test, rozszerzyć) | `admin.py` + `tests_admin_linking.py` |
| bulk API (`import_products_bulk`, `bulk-map`) — walidacja + zapis              | `views.py`, komendy                   |
| `_bulk_import_products` / `_bulk_update_inventory` — batch, konflikt, dedup    | `tasks.py`                            |
| watchdog `watchdog_import_healthcheck` — wykrycie zawieszonego importu         | `tasks.py`                            |
| komendy `sync_products` / `sync_inventory` / `sync_variants` z mockiem API     | `management/commands`                 |

### E2E (pełny pipeline, HTTP mockowany `responses`)

| Scenariusz                                                                             | Asercje                                                                                        |
| -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `full_import_and_update` — ITEMS 2 strony + INVENTORY, `responses` zwraca fixture JSON | Brand/Category/Product/Variant/Image w matterhorn1, `ApiSyncLog` OK, znacznik ostatniej strony |
| wznowienie importu od przerwanej strony (rozszerzyć `tests_import_resume`)             | start od zapisanej strony, nie od 1                                                            |
| import → `mpd_create` → linkowanie po EAN                                              | produkt w MPD, `ProductvariantsSources` dopięte, warianty bez trafienia w panelu „orphaned"    |
| import z częściowym błędem API (500 na stronie 2)                                      | strona 1 zapisana, retry/log, brak duplikatów po ponowieniu                                    |
| blokada równoległego importu (`matterhorn1_full_import_lock`)                          | drugi start → `skipped`                                                                        |
| aktualizacja INVENTORY zmienia stan → `StockHistory` + `track_stock_changes`           | wpis historii, event                                                                           |

---

## Fazy realizacji

| Faza  | Zakres                                                                                                                                                                                                                          | Stan |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- |
| **0** | Infra pytest-django (wyżej)                                                                                                                                                                                                     | ✅   |
| **1** | Pakiet `matterhorn1/tests/`: `factories.py` (buildery ładunków API), `mock_matterhorn.py` (`responses` helpery ITEMS/INVENTORY), `conftest.py` (fixture'y), pierwszy e2e importu + unit `_parse_creation_date`                  | ✅   |
| **2** | Unit: `_prepare_product_create/update`, `stock_tracker`, `transaction_logger` (`database_utils` = martwy kod, pominięty)                                                                                                        | ✅   |
| **3** | Integration: silnik sagi (kompensacja / propagacja / logi), `_bulk_import_products` + `_bulk_update_inventory`, watchdog                                                                                                        | ✅   |
| **4** | E2E błędów: chwilowy 500 na str. 2, blokada równoległa, wznowienie od strony, pusta odpowiedź, produkt bez wariantów; admin `assign_mapping`. `mpd_create` (7-krokowa saga + upload + HTTP kompensacja) — do osobnego podejścia | ✅   |
| **5** | Próg pokrycia w CI (`--cov-fail-under`), raport, białe plamy                                                                                                                                                                    | ⬜   |

Cel pokrycia matterhorn1: **linie ≥ 80%**, `tasks.py` i `saga.py` ≥ 75%.

### Struktura `matterhorn1/tests/`

```
matterhorn1/
  tests_api.py            # legacy (był tests.py) — testy DRF ViewSetów
  tests_models.py         # legacy
  tests_serializers.py    # legacy
  tests_saga*.py          # legacy
  tests_import_resume.py  # legacy
  tests_admin_linking.py  # legacy
  tests/
    factories.py          # api_item(), api_variant(), inventory_record()
    mock_matterhorn.py    # mock_items(rsps, pages), mock_inventory(...), mock_items_error(...)
    conftest.py           # no_sleep (autouse), matterhorn_api, mocked_responses, prior_items_sync
    tests_unit_*.py       # @pytest.mark.unit
    tests_integration_*.py # @pytest.mark.integration
    tests_e2e_*.py         # @pytest.mark.e2e
```

Legacy `tests_*.py` zostają w korzeniu apki (przenoszenie zepsułoby `from .models`).

---

## Konwencje (po migracji)

- nowe testy: plik `tests_<obszar>.py` (collector zbiera `tests*.py`, **nie** `test_*.py` — to koliduje z komendami `test_*_connection.py`), styl pytest (funkcje + fixture, `@pytest.mark.django_db`)
- markery: `@pytest.mark.unit` / `integration` / `e2e`; `pytest -m "not e2e"` do szybkiego cyklu
- HTTP: **zawsze** przez fixture `mocked_responses` (`responses.RequestsMock`) + helpery z `mock_matterhorn.py` — żaden test nie dzwoni po sieci
- Celery: `CELERY_TASK_ALWAYS_EAGER` (już włączone w trybie testów) — taski wołane synchronicznie
- ładunki API budowane funkcjami z `matterhorn1/tests/factories.py`, nie surowym JSON-em (łatwiej parametryzować)
- jeden `assert` logiczny na test gdy się da; nazwy `test_<co>_<warunek>_<oczekiwanie>`
