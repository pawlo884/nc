# nc_project — przegląd projektu

Dokument wysokopoziomowy: co to jest, z czego się składa, jak dane płyną i
jaki jest stan techniczny. Diagram: [ARCHITECTURE.md](ARCHITECTURE.md).
Szczegółowy opis przepływów krok po kroku + status funkcji:
[HOW_IT_WORKS.md](HOW_IT_WORKS.md).

## 1. Po co to jest

Centralny **hub katalogu produktów (MPD)**. Trzy hurtownie (Matterhorn, Tabu,
Mada) są importowane niezależnie do własnych baz, mapowane po **EAN** do jednej
bazy MPD, a z MPD dane wychodzą dwoma kanałami do sklepów:

- **plik XML w formacie IOF 3.0** — pobierany przez IdoSell / IAI,
- **push przez WebAPI do PrestaShop**.

Operator zarządza katalogiem z Django Admina; Claude czyta katalog przez
lokalny serwer MCP (read-only).

## 2. Stack

| Warstwa  | Technologia                                                                                                                                                            |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend  | Django 6.0, DRF 3.17, Python 3.13                                                                                                                                      |
| Async    | Celery 5.4 + Redis (**tylko broker**); wyniki i harmonogram w PostgreSQL (`django-celery-results`, `django-celery-beat`)                                               |
| Bazy     | PostgreSQL, **osobna baza per aplikacja** + routery; w DEV prefiks `zzz_`                                                                                              |
| Pliki    | MinIO / S3 (`django-storages`) — wygenerowane XML-e i zdjęcia                                                                                                          |
| Frontend | React 19 + Vite + TS, TanStack Query, react-router (`frontend/mpd/`), SPA pod `/mpd-app/`                                                                              |
| AI       | `openai` + `openai-agents` + `langchain-openai` (web_agent); `mcp` (serwer katalogu)                                                                                   |
| Scraping | Selenium (web_agent — wypełnianie formularzy)                                                                                                                          |
| Docs API | drf-spectacular (`/api/docs/`, `/api/redoc/`)                                                                                                                          |
| Deploy   | prod + dev: **jeden `docker-compose`** (prod: obraz wypalony, NPM z przodu; dev: bind-mount + tunel SSH). Patrz [DEPLOY.md](DEPLOY.md)                                 |
| CI/CD    | GitHub Actions, semantic-release (Conventional Commits → CHANGELOG → tag); deploy prod **ręczny** (`workflow_dispatch` / `scripts/deploy-prod.sh`), husky + commitlint |

## 3. Aplikacje (`src/apps/`)

| App             | Rola                                                                                                                                                                                                               |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **MPD**         | Serce systemu. Modele katalogu, eksport XML (full / light / gateway / stocks / units), REST API `/api/mpd/…`, widoki zarządzania produktami, adaptery hurtowni (`source_adapters/`), linkowanie po EAN, serwer MCP |
| **matterhorn1** | Import z Matterhorn B2B API (własna baza-lustro), saga mapująca produkty/warianty do MPD, tracker stanów, watchdog importu — **dok.: [`matterhorn/MATTERHORN1.md`](matterhorn/MATTERHORN1.md)**                    |
| **web_agent**   | Automatyzacja: taski Celery + Selenium wypełniające formularze MPD, procesor AI (OpenAI / LangChain), modele `AutomationRun` / `ProductProcessingLog`, API `/api/web-agent/…`                                      |
| **tabu**        | Import z Tabu REST API + saga do MPD, `services.py`, pg-advisory-locki — **dok.: [`tabu/TABU.md`](tabu/TABU.md)**                                                                                                  |
| **mada**        | Import z feedu XML Mada (`parser.py` + `importer.py` + `api_client.py`) + saga, cleanup osieroconych mapowań — **dok.: [`mada/MADA.md`](mada/MADA.md)**                                                            |
| **prestashop**  | Kanał wyjściowy (nie import): budowa i push produktów MPD do PrestaShop WebAPI. Faza 1 gotowa, uruchamiany ręcznie (`manage.py push_prestashop_product`)                                                           |

## 4. `src/core/`

- **`db_routers.py`** — 6 routerów (po jednym na app + `DefaultRouter` dla tabel systemowych). Lazy-wybór `zzz_*` vs prod. `CONN_MAX_AGE=0` wymuszony przez routing.
- **`db_backend/`** — własny backend PostgreSQL owijający Django o retry logic (8 prób, exponential backoff) — po restarcie Dockera tunel SSH potrzebuje czasu.
- **`saga.py` + `saga_models.py`** — wspólny wzorzec Saga (execute/compensate, kompensacja w odwrotnej kolejności, logowanie do bazy fail-open) używany przez matterhorn1/tabu/mada przy operacjach na 2 bazach.
- **`pg_locks.py`** — rozproszone blokady na PostgreSQL advisory locks (zastąpiły `cache.add` na Redisie).
- **`middleware.py`** — `DynamicDebugMiddleware` (DEBUG zależny od IP klienta) + `BotBlockerMiddleware`.
- **`mpd_spa.py`** — serwuje build Vite pod tą samą ścieżką co dev (`/mpd-app/`).
- **`wholesaler_admin/`** — wspólne klocki adminów hurtowni (fuzzy matching, filtry, miniatury, historia stanów).

## 5. Bazy danych

Multi-DB: `default` (systemowe + cache + celery-results), `MPD`, `matterhorn1`,
`web_agent`, `tabu`, `mada`. Każda ma bliźniaczy wpis `zzz_*` w DEV.

W testach routing jest wyłączony — wszystko idzie do `default`, reszta baz to
`MIRROR: default`.

## 6. Celery / zadania okresowe

- Workery: **`celery-fast`** (`-Q default`, concurrency 3) — częste/krótkie taski; **`celery-heavy`** (`-Q import,heavy`, concurrency 2) — `matterhorn1.full_import_and_update` + długie/rzadkie (`tabu.sync_tabu_products_update`, `web_agent.automate_*`, `mada.sync_mada_full`, `MPD.link_all_products_to_new_source`); `celery-beat`; `flower`. `celery-ml` (`-Q ml`) = szkielet, nieużywany.
- Harmonogram w Django Admin → Periodic Tasks; rejestrują go komendy `setup_*_task.py` w każdej appce.
- Cykle: import hurtowni ~co 10 min; eksport `full.xml` / `full_change.xml` przyrostowo co godzinę, pełny raz dziennie (domyślnie wyłączony); sync stanów Mada 15 min / dziennie.
- Monitoring: Flower (`:5555`).

## 7. Eksport

- **XML** (`apps/MPD/export_to_xml.py`): `FullXMLExporter` + warianty light / gateway / stocks. Śledzenie zmian po `updated_at` / `last_updated` w kilku tabelach; znacznik ostatniego pełnego eksportu w `FullChangeFile`. Wynik → MinIO.
- **PrestaShop** (`apps/prestashop/exporter.py`): twarda kolejność `kategoria + kolory/rozmiary → produkt → combinations → stock_available`. Reguła kodu producenta (`ean → gtin14 → gtin13 → producer_code → other`) współdzielona z eksportem XML — oba kanały muszą dawać ten sam SKU.

## 8. Frontend (`frontend/mpd/`)

React SPA do przeglądania/edycji katalogu MPD: lista produktów, szczegół z
wariantami/zdjęciami/cenami, panel **orphan variants** (warianty hurtowni
niedopasowane po EAN), grupowanie zdjęć po kolorze, auth tokenem. Build trafia
do obrazu Dockera i jest serwowany przez Django pod `/mpd-app/`; w dev to Vite
na `:5173`.

## 9. Deploy

Pełny opis: **[DEPLOY.md](DEPLOY.md)**. k3s i blue-green **usunięte** (#259).

- **Prod:** jeden `docker-compose/docker-compose.prod.yml` na VPS. Obraz
  `nc-django-app:latest` z wypalonym kodem + React SPA + `collectstatic`
  (`Dockerfile.prod`). **NPM** (Nginx Proxy Manager) → `web:8000` (gunicorn +
  whitenoise). Serwisy: `web`, `celery-fast`, `celery-heavy`, `celery-beat`,
  `flower`, `redis`, `migrate` (profil). Postgres (`nc-postgres-1`) osobno
  (profil `shared`). Deploy: `scripts/deploy-prod.sh <ref>` (`git reset` →
  build → migracje → `up -d`), ręcznie albo `deploy-vps.yml` (`workflow_dispatch`).
- **Dev:** `docker-compose/docker-compose.dev.yml` — `web`, `nginx` (:8090),
  `celery-fast`, `celery-heavy`, `celery-beat`, `flower`, `redis`,
  `postgres-ssh-tunnel` (baza dev zdalna przez tunel SSH), `static-init`.
  `src/` bind-mount = hot reload.
- **ML:** `docker-compose.dev.ml.yml` — nakładka z `celery-ml` (`-Q ml`),
  szkielet, nieużywana (`ML_CONTAINER_TODO.md`).

## 10. Testy

~36 plików testowych, ~56 migracji. Pokrycie: modele każdej appki, sagi,
serializery, eksport XML, API MPD, adaptery hurtowni, pg-locki, serwer MCP.

## 11. Dług techniczny / obserwacje

| Obserwacja                                                                                    | Status                             |
| --------------------------------------------------------------------------------------------- | ---------------------------------- |
| `matterhorn1/tasks.py.rej`, `web_agent/automation/browser_automation.py.bak` — pliki-śmieci   | do usunięcia                       |
| `producer_catalog` / `dashboard_pydash` — puste katalogi po usuniętych appkach (tylko `.pyc`) | do usunięcia                       |
| 8× zduplikowany blok `DATABASES` w `settings/base.py` (~150 linii)                            | refaktor do pętli/helpera          |
| `DynamicDebugMiddleware` włącza DEBUG na podstawie IP klienta                                 | przejrzeć pod kątem bezpieczeństwa |
| PrestaShop: push tylko ręczny, `SHOP_ID` zahardkodowany                                       | Faza 4 (automatyzacja) niewdrożona |
| Zgodność z IOF 3.0 XSD niepełna (modele, wymagane pola, FK zamiast `*_id`)                    | Issues #177–#183                   |
| Brak `CLAUDE.md` w root; `agents.md` opisuje skille Cursora                                   | kosmetyka                          |
