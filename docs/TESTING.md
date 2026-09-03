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

## Faza 0 — migracja na pytest-django (infra)

Jeden PR, bez nowych testów logiki — tylko przełączenie runnera tak, żeby
istniejące ~98 testów przechodziło 1:1.

- [ ] `requirements.ci.txt` (+ `requirements.txt`): `pytest`, `pytest-django`, `pytest-cov`, `responses`
- [ ] `pyproject.toml` → `[tool.pytest.ini_options]`:
  - `DJANGO_SETTINGS_MODULE = "core.settings.dev"`
  - `python_files = "tests*.py test_*.py"` (zgodność ze starą i nową nazwą)
  - `testpaths = ["src/apps"]`, `pythonpath = ["src", "src/apps"]`
  - `addopts = "--reuse-db --nomigrations -p no:randomly"` (do rozważenia)
  - markery: `unit`, `integration`, `e2e`
- [ ] **`core/settings/dev.py`**: `if 'test' in sys.argv` (2 miejsca: linia 137 i 251) → wspólny flag
  ```python
  RUNNING_TESTS = 'test' in sys.argv or 'pytest' in sys.modules
  ```
  Inaczej pod pytest nie zadziała: wyłączony routing baz, `DummyCache`,
  wyłączony throttling, `CELERY_TASK_ALWAYS_EAGER`.
- [ ] `conftest.py` (root): wspólne fixture'y — `api_client`, `admin_user` + token,
      `mpd_db`/`matterhorn1_db` markery baz
- [ ] `.github/workflows/check-branch.yml`: krok „Testy Django" → `pytest` (+ `--cov=apps --cov-report=term-missing`)
- [ ] `docs/HOW_TO_FIX_TESTS.md` / `HOW_IT_WORKS.md` — zaktualizować komendę uruchamiania
- [ ] weryfikacja: `pytest src/apps/matterhorn1` = tyle samo pass co `manage.py test matterhorn1`

> Uwaga o bazach: `dev.py` w trybie testów wyłącza routery (`DATABASE_ROUTERS = []`)
> — wszystkie modele idą do `default`, pozostałe bazy to `MIRROR: default`.
> Wywołania `.using('MPD')` w kodzie nadal działają (alias → ta sama baza testowa).
> Klasy testów cross-DB deklarują `databases = {'default', 'MPD', ...}`.

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

| Faza  | Zakres                                                                                                                     | PR          |
| ----- | -------------------------------------------------------------------------------------------------------------------------- | ----------- |
| **0** | Infra pytest-django (wyżej)                                                                                                | 1           |
| **1** | Fixtures + `responses` helpers dla API Matterhorn (`tests/fixtures/matterhorn/*.json`), reorganizacja plików w `tests/unit | integration | e2e` | 1   |
| **2** | Unit: `tasks.py` helpery, `stock_tracker`, `transaction_logger`, `database_utils`, braki w serializerach                   | 1–2         |
| **3** | Integration: `saga.py` (happy + kompensacja), admin `mpd_create`/`assign_mapping`, `_bulk_*`, watchdog                     | 2–3         |
| **4** | E2E: `full_import_and_update` z `responses`, import→map→link, scenariusze błędów                                           | 2           |
| **5** | Próg pokrycia w CI (`--cov-fail-under`), raport, uzupełnienie białych plam                                                 | 1           |

Cel pokrycia matterhorn1: **linie ≥ 80%**, `tasks.py` i `saga.py` ≥ 75%.

---

## Konwencje (po migracji)

- nowe testy: `test_*.py`, styl pytest (funkcje + fixture, `@pytest.mark.django_db`)
- markery: `@pytest.mark.unit` / `integration` / `e2e`; `pytest -m "not e2e"` do szybkiego cyklu
- HTTP: **zawsze** `@responses.activate` — żaden test nie dzwoni po sieci
- Celery: `CELERY_TASK_ALWAYS_EAGER` (już włączone w trybie testów) — taski wołane synchronicznie
- fixtures API w `src/apps/matterhorn1/tests/fixtures/` (prawdziwe kształty odpowiedzi, zanonimizowane)
- jeden `assert` logiczny na test gdy się da; nazwy `test_<co>_<warunek>_<oczekiwanie>`
