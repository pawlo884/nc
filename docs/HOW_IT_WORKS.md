# nc_project — jak to działa (przepływy)

Uzupełnienie [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) (wysokopoziomowe „co")
i [ARCHITECTURE.md](ARCHITECTURE.md) (diagram) o szczegółowy opis **jak** —
przepływ po przepływie. Stan: v1.44.3 (2026-09-03).

## Spis

- [A. Status — co jest zrobione](#a-status--co-jest-zrobione)
- [B. Architektura (skrót)](#b-architektura-skrót)
- [C. Przepływy krok po kroku](#c-przepływy-krok-po-kroku)
- [D. Infrastruktura](#d-infrastruktura)
- [E. Dług techniczny](#e-dług-techniczny)

---

## A. Status — co jest zrobione

| Obszar                                           | Stan              | Uwaga                                                                                      |
| ------------------------------------------------ | ----------------- | ------------------------------------------------------------------------------------------ |
| Import Matterhorn                                | ✅ prod           | `full_import_and_update` (kolejka `import`); od PR #204 wznawia od przerwanej strony ITEMS |
| Import Tabu                                      | ✅ prod           | REST API + saga, pg-advisory-locki, watchdog locka                                         |
| Import Mada                                      | ✅ prod           | feed XML + saga, cleanup pustych/osieroconych                                              |
| Linkowanie po EAN                                | ✅ prod           | adaptery `source_adapters/`, panel „orphaned"                                              |
| Mapowanie ręczne (admin)                         | ✅ prod           | `mpd_create` / `assign_mapping` per hurtownia, wspólny `core/wholesaler_admin/`            |
| Mapowanie per kolor hurtowni                     | ✅ prod           | `producer_color` na wariancie/zdjęciu (v1.41)                                              |
| Eksport XML IOF 3.0                              | ✅ prod           | full / full_change / light / gateway + słowniki                                            |
| Eksport PrestaShop                               | 🟡 Faza 1         | tylko ręczny `push_prestashop_product --id`; bulk/cron = Faza 4                            |
| AI pipeline (LangChain+OpenRouter+LangSmith)     | ✅ v1.44.0 (#201) | opt-in `USE_LANGCHAIN_AI=1`; fix liczenia fallbacku v1.44.1                                |
| Automatyzacja formularzy (Selenium)              | ✅ prod           | `automate_mpd_form_filling` (Matterhorn/przeglądarka), `automate_tabu_to_mpd` (backend)    |
| MCP server (katalog MPD read-only)               | ✅ v1.43          | stdio, 4 narzędzia, `sync_to_async` fix v1.43.2                                            |
| Frontend SPA (React)                             | ✅ prod           | login, lista, szczegół produktu                                                            |
| Deploy k3s                                       | ✅ prod           | od #206 jeden `COPY src/apps/`                                                             |
| wega (4. hurtownia)                              | 🔴 R&D            | brak dostępu do API; `zzz_wega` + `WEGA_DB_NAME` to celowa infra                           |
| producer_catalog (scraper AVA), dashboard_pydash | 🔴 dead           | kod usunięty, zostały puste katalogi                                                       |

Otwarte issues: #177–#181 (IOF 3.0), #182 (wspólne EAN 3 hurtownie), #187 (sprzątanie), #188 (refaktor `DATABASES`), #195 (tracking AI).

---

## B. Architektura (skrót)

```
  HURTOWNIE            IMPORT (osobna baza + saga)        HUB           EKSPORT            SKLEPY
 Matterhorn  ─B2B────▶ matterhorn1 (zzz_matterhorn1) ┐
 Tabu        ─REST───▶ tabu        (zzz_tabu)        ┼──▶  MPD  ──▶ XML full/light/  ──▶ IdoSell/IAI
 Mada        ─feed───▶ mada        (zzz_mada)        ┘   (zzz_MPD)   gateway/change
                       web_agent (Selenium + AI) ·········▶ │      + słowniki → MinIO
                       zzz_web_agent                        │
                                              ┌─────────────┴───────────┐   prestashop app ──▶ PrestaShop
                                        Django Admin              MCP server (stdio)           WebAPI (ręczny)
                                        (operator)                Claude (read-only)

 Celery Beat + Redis(broker) ──wyzwala──▶ importy, eksporty, sync stanów, cleanup
 django-celery-results / -beat ──▶ wyniki + harmonogram w PostgreSQL (baza default)
```

Bazy (PostgreSQL, osobna per apka, router `core/db_routers.py`): `default`
(systemowe + cache `nc_cache_table` + celery-results), `MPD`, `matterhorn1`,
`web_agent`, `tabu`, `mada` (+ `zzz_*` w dev; dev łączy się do zdalnej bazy
przez kontener `postgres-ssh-tunnel`).

---

## C. Przepływy krok po kroku

### 1. Import z hurtowni → własna baza-lustro

Każda hurtownia ma model odzwierciedlający jej API i task Celery. Import
**nie dotyka MPD** — tylko wypełnia bazę hurtowni.

**Matterhorn** — `full_import_and_update` (kolejka `import`, osobny worker `celery-import`):

1. `_check_database_connection()` — jak baza padła, przerywa
2. blokada `cache.add('matterhorn1_full_import_lock', ...)` (DatabaseCache, 1h) — brak równoległych importów
3. czyści stare/wiszące rekordy `running`
4. import ITEMS **od ostatniego zaimportowanego ID** (lub przerwanej strony — PR #204), batch 100
5. po ITEMS automatycznie odpala aktualizację INVENTORY (stany)
6. `auto_continue=True` → pętla aż skończą się produkty
7. watchdog `watchdog_import_healthcheck` pilnuje że import nie zawisł

**Tabu** — `sync_tabu_products_update` (~60 min), `sync_tabu_stock` (~10 min),
`sync_tabu_categories` (dziennie). Sekcja krytyczna pod
`core.pg_locks.advisory_lock` — advisory lock zamiast TTL w cache: zwalnia się
automatycznie gdy proces padnie, nie wygasa w trakcie długiego importu.

**Mada** — `sync_mada_full` (crontab 00:15), `sync_mada_partial` (~15 min),
`cleanup_empty_products` (01:00).

### 2. Hurtownia → MPD: Saga (dwie bazy)

Przeniesienie produktu do MPD idzie przez `core.saga.BaseSagaOrchestrator`
(wspólny); każda hurtownia ma cienką podklasę wskazującą swoje modele
`Saga`/`SagaStep` i alias bazy.

```
Krok 1: _saga_create_mpd_<h>     → tworzy Products + ProductVariants + Sources w MPD
        compensate: _saga_delete_mpd_<h>        (usuwa z MPD)
Krok 2: _saga_update_<h>_mapping  → zapisuje mapped_product_uid / mapped_variant_uid w hurtowni
        compensate: _saga_clear_<h>_mapping
```

Jak krok 2 padnie → kompensacja kroku 1 usuwa świeżo utworzony produkt z MPD
(brak sieroty). Postęp logowany do bazy hurtowni **fail-open** (błąd logu nie
przerywa sagi). `merge_result_into_own_step_data` przekazuje `mpd_product_id`
z execute do compensate.

Wyzwalane: **ręcznie w adminie hurtowni** (`mpd_create` = nowy produkt MPD
z formularza, `assign_mapping` = podpięcie do istniejącego) albo przez
**web_agent** (automatyzacja).

### 3. Linkowanie po EAN

`source_adapters/linking.py`. Gdy produkt MPD dostał źródło (np. z Matterhorn),
`link_variants_from_other_sources(mpd_product_id, current_source_id)`:

1. zbiera EAN-y wszystkich wariantów produktu
2. dla każdej **innej** hurtowni woła jej adapter `get_variants_by_eans(ean_list)`
3. na trafienie: `get_or_create` `ProductvariantsSources` (ean, `variant_uid`
   tylko jeśli mieści się w PG int32, `producer_code` tylko gdy jawny) +
   `StockAndPrices` + ustawia `mapped_product_uid` / `mapped_variant_uid`
   w hurtowni źródłowej
4. **świadomie NIE tworzy** wariantów dla EAN-ów spoza MPD — hurtownie trzymają
   kilka kolorów pod jednym produktem, nazwy kolorów się rozjeżdżają
   („czarny" vs „black"). Takie warianty → panel **„orphaned"** na karcie
   produktu (SPA `OrphanVariantsPanel`, API `/api/mpd/products/<id>/orphan-variants/`),
   dopina się ręcznie lub automatycznie gdy powstanie właściwy produkt.

`link_all_products_to_new_source(new_source_id)` — jednorazowo przy dodaniu
nowej hurtowni, przechodzi wszystkie produkty MPD.

### 4. Eksport XML (IOF 3.0) → MinIO → IdoSell

`apps/MPD/export_to_xml.py` (~2700 LOC), hierarchia `BaseXMLExporter`:

| Eksporter                                                                            | Co                                                     | Kiedy                                         |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------ | --------------------------------------------- |
| `FullXMLExporter`                                                                    | pełny katalog / przyrostowo od ostatniego `full.xml`   | co godzinę (przyrost), dziennie (pełny, opc.) |
| `FullChangeXMLExporter`                                                              | produkty zmienione w ost. 2h **już obecne w full.xml** | co godzinę                                    |
| `LightXMLExporter`                                                                   | zmiany z ost. godziny                                  | co godzinę                                    |
| `GatewayXMLExporter`                                                                 | per źródło (magazyn)                                   | po eksporcie (`refresh_gateway_after_export`) |
| `Producers / Stocks / Units / Categories / Sizes / Parameters / Series / Warranties` | słowniki                                               | na żądanie z adminu (`/mpd/generate-*-xml/`)  |

Śledzenie zmian: `updated_at` na `products` / `product_variants` /
`product_variants_retail_price`, `last_updated` na `stock_and_prices`,
`updated_at` na `product_images`. Znacznik ostatniego pełnego eksportu w tabeli
`full_change_files`. Flaga `exported_to_iai` na wariancie +
`mark_existing_variants_as_exported()`.

Kod producenta (SKU): fallback `ean → gtin14 → gtin13 → producer_code → other`
— **ta sama reguła** w `export_to_xml.py`, `prestashop/exporter.py`
i `run_mcp_server.py` (muszą się zgadzać).

### 5. Eksport PrestaShop (Faza 1, ręczny)

`push_prestashop_product --id=<MPD id> [--dry-run]`. Twarda kolejność
(PrestaShop wymaga, by obiekty istniały przed referencją):

```
ensure_category + ensure_color_value / ensure_size_value   (mapping.py, zapisuje presta_*_id w MPD)
  → push_product        (state=1, Product::STATE_SAVED)
    → push_combination  (1 na wariant)
      → push_stock      (stock_available, id_shop=1 — inaczej niewidoczne w adminie PrestaShop)
```

ID-ki PrestaShop zapisywane z powrotem w MPD (`presta_product_id`,
`presta_combination_id`, `Colors.presta_option_value_id`,
`Paths.presta_category_id`, `Brands.presta_manufacturer_id`).

### 6. AI pipeline (web_agent) — wzbogacanie danych produktu

`get_ai_processor()` → `LangChainAIProcessor` gdy `USE_LANGCHAIN_AI=1`, inaczej
legacy `AIProcessor` (~2500 LOC, bezpośredni OpenAI, ścieżki
openai / huggingface / Novita).

`LangChainAIProcessor` (`automation/langchain_ai_processor.py`):

- `ChatOpenAI(base_url=openrouter.ai/api/v1)`, primary
  `moonshotai/kimi-k2-thinking` + fallback `openai/gpt-4o-mini`, spięte
  `.with_fallbacks()` → każda próba osobnym spanem w LangSmith
- `kimi` (model rozumujący) dostaje `extra_body={"reasoning":{"effort":"low"}}`
  — bez tego reasoning_tokens zjadają cały budżet i JSON się nie kończy
- prompty z bazy (`AIPrompt`, edytowalne w Django Admin, `is_active`,
  `render()`) z fallbackiem hardkodowanym
- operacje: `enhance_product_name`, `enhance_product_description` (rozróżnia
  kostium vs figi), `create_short_description`,
  `extract_attributes_from_description` — wszystkie ze `structured_output`
  (Pydantic)
- **2 niezależne mechanizmy kontroli**: (1) LangSmith ambient
  (`LANGSMITH_TRACING=true` + klucz) + tagi/metadata; (2) `_CallLogCallback`
  → `pop_call_log()` → `ProductProcessingLog.processing_data["_ai_pipeline"]`
  (który model, sukces/błąd, czas) — widoczne w adminie bez otwierania LangSmith

Plan rozwoju (routing modeli per zadanie, observability): [AI_STACK_PLAN.md](AI_STACK_PLAN.md), tracking #195.

### 7. Automatyzacja formularzy MPD (Selenium)

`automate_mpd_form_filling(brand_id, category_id, filters)`:

1. tworzy `AutomationRun` (status `running`)
2. `BrowserAutomation` loguje się do Django Admina, `ProductProcessor` łączy
   przeglądarkę z AI
3. pobiera produkty z bazy `matterhorn1` (surowy SQL); per produkt:
   - `ProductProcessingLog`
   - dane → `ai_processor.process_product_data()` (name / description / short_description)
   - wypełnia formularz MPD w przeglądarce, zapisuje
   - `product_log.processing_data = result` + `_ai_pipeline`
4. `automate_tabu_to_mpd` — wariant backendowy (bez przeglądarki, przez saga
   `create_mpd_product_from_tabu`)

### 8. MCP server

`manage.py run_mcp_server` (stdio, read-only): `search_products`,
`get_product`, `get_stock_by_ean`, `list_categories`. Zero
`.save()/.create()`. Każde narzędzie owinięte `sync_to_async` (FastMCP woła
sync w pętli asyncio, Django ORM tego zabrania). Konfiguracja klienta:
[MCP_SERVER.md](MCP_SERVER.md).

### 9. Frontend SPA (`frontend/mpd/`)

React 19 + Vite + TanStack Query, 3 strony (`LoginPage`, `ProductsPage`,
`ProductDetailPage`). Auth tokenem (`/api/auth/token/`). Panele: warianty,
zdjęcia (grupowanie po kolorze), orphaned, atrybuty / tkaniny / ścieżki, ceny
detaliczne. Build → obraz Dockera, serwowany przez Django pod `/mpd-app/`
(`core/mpd_spa.py`); dev = Vite `:5173`.

---

## D. Infrastruktura

- **Celery**: kolejki `default` (worker `celery-default`) + `import` (worker
  `celery-import`, tylko ciężki import Matterhorn) + opc. `ml`. Beat =
  `DatabaseScheduler`. Broker Redis, reszta (wyniki, harmonogram, cache, część
  locków) w PostgreSQL.
- **Harmonogram** (Django Admin → Periodic Tasks, rejestrowany
  `setup_*_task.py`): stany MPD ← Matterhorn co ~5 min, Tabu stany ~10 min /
  produkty ~60 min / kategorie dziennie, Mada partial ~15 min / full 00:15 /
  cleanup 01:00, eksport XML full + change co godzinę.
- **Deploy prod**: `Release` (semantic-release, Conventional Commits →
  CHANGELOG → tag `v*`) → `deploy-vps.yml` → `scripts/k8s-prod/deploy.sh` na
  k3s. Manifesty `deployments/k8s/nc-prod/` (web, celery, flower, redis,
  ingress, migrate-job). `Dockerfile.prod` wypala `collectstatic --clear`
  w build.
- **Deploy dev**: `docker-compose/docker-compose.dev.yml` — web, nginx `:8090`,
  3× celery, flower `:5555`, redis, `postgres-ssh-tunnel` (baza zdalna),
  `static-init`. `src/` bind-mount = hot reload.
- **CI**: `check-branch.yml` (PR), `deploy-test.yml` (k3s test), `release.yml`.
  `deploy.yml` (DigitalOcean) DEPRECATED.
- **Testy**: ~38 plików, ~56 migracji.

---

## E. Dług techniczny

| Rzecz                                                                                                  | Waga                         | Ślad          |
| ------------------------------------------------------------------------------------------------------ | ---------------------------- | ------------- |
| `matterhorn1/tasks.py.rej`, `browser_automation.py.bak`, puste `producer_catalog` / `dashboard_pydash` | niska                        | #187          |
| 8× zduplikowany blok `DATABASES`; `zzz_default` / `zzz_MPD` w base.py tworzą podwójne aliasy w prod    | średnia                      | #188          |
| `DynamicDebugMiddleware` — DEBUG wg IP klienta                                                         | przejrzeć pod bezpieczeństwo | —             |
| 2 równoległe warstwy AI (`AIProcessor` ~2500 LOC + `LangChainAIProcessor`), legacy wciąż domyślny      | plan                         | #195          |
| `openai-agents` w `requirements.txt`, nieużywany                                                       | usunąć albo zaplanować       | #195 (Faza 4) |
| 2 modele kategorii (`Categories` legacy + `Paths` używany)                                             | do wyjaśnienia               | —             |
| Matterhorn import trzyma lock w cache (1h TTL) zamiast pg_locks jak tabu/mada                          | niespójność                  | —             |
| PrestaShop: ręczny push, `SHOP_ID` zahardkodowany                                                      | Faza 4                       | —             |
