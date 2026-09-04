# NC (nc_project)

Projekt Django + PostgreSQL + Celery/Redis. **Produkcja działa na k3s** (`deployments/k8s/nc-prod`, patrz `docs/K8S_PROD.md`). Tryb blue‑green (`docker-compose.services.yml`) jest **DEPRECATED** — zachowany tylko do wglądu/awaryjnego rollbacku.

## Wymagania
- **Docker + Docker Compose** (w praktyce: Docker Desktop na Windows).
- **PostgreSQL** dostępny z kontenerów (w DEV najczęściej `host.docker.internal:5432`).
- **Git**.
- (Opcjonalnie) **Python 3.13** tylko jeśli chcesz uruchamiać bez Dockera.
  - Zalecane: **pyenv** do zarządzania wersjami Pythona (projekt ma plik `.python-version`).
  - Po wejściu do katalogu projektu pyenv automatycznie aktywuje odpowiednią wersję.
  - **Konfiguracja pyenv**: Zobacz `docs/PYENV_SETUP.md` jeśli masz problemy z konfiguracją.

## Struktura repo (najważniejsze)
- `src/core/` – konfiguracja projektu (settings, urls, celery, db_routers)
- `src/apps/` – aplikacje Django (poniżej opis)
- **manage.py** – w katalogu `src/` (uruchomienie: `cd src && python manage.py ...` lub `python src/manage.py ...`)
- `deployments/docker/` – Dockerfile dev/prod/ML + entrypoint
- `docker-compose*.yml` – definicje usług (dev, dev+ML, blue‑green prod **[DEPRECATED]**)
- `scripts/` – skrypty (build, deploy, migracje, security, monitoring)
- `docs/` – dokumentacja (quick start, deploy, struktura, API itp.)

## Co jest w projekcie (aplikacje)

- **`src/apps/matterhorn1/`** – integracja z hurtownią Matterhorn:
  - import produktów/variantów/zdjęć do lokalnej bazy `matterhorn1`,
  - modele odzwierciedlające API hurtowni,
  - saga (`saga.py`, `saga_variants.py`) mapująca produkty do MPD.

- **`src/apps/MPD/`** – moduł MPD (nasza docelowa baza produktów):
  - modele produktów, wariantów, źródeł (`ProductVariants`, `ProductvariantsSources`, `StockAndPrices` itd.),
  - eksport XML (pełny, przyrostowy, gateway, light, stocks, units…),
  - widoki do zarządzania produktami (tworzenie/aktualizacja/bulk) i generowania XML,
  - REST API pod `/mpd/` oraz `/api/mpd/…` (m.in. `product-sets`, zarządzanie ścieżkami, atrybutami, mapowanie z `matterhorn1`).

- **`src/apps/web_agent/`** – web‑owy agent automatyzacji:
  - modele i API do uruchamiania automatyzacji (`AutomationRun`, `ProductProcessingLog`),
  - taski Celery do wypełniania formularzy MPD na podstawie danych z hurtowni,
  - REST API pod `/api/web-agent/…` (uruchamianie automatyzacji, podgląd logów).

- **`src/apps/tabu/`** – integracja z hurtownią Tabu:
  - modele lustrzane danych Tabu,
  - logika mapowania produktów Tabu → MPD (analogicznie do `matterhorn1`).

- **Inne elementy**
  - **Celery + Redis** – kolejki (`celery-default`, opcjonalnie ML worker), monitoring przez Flower.
  - **drf-spectacular** – dokumentacja REST API pod `/api/schema/`, `/api/docs/`, `/api/redoc/`.
  - **Deploy na k3s** – pełny pipeline deployu na VPS (`deployments/k8s/nc-prod`, `scripts/k8s-prod`, `.github/workflows/deploy-vps.yml`). Blue‑green (`scripts/deploy`) jest **DEPRECATED**.

## Konfiguracja środowiska (`.env.dev`)
Plik **`.env.dev` nie jest wersjonowany** (jest ignorowany) – musisz go mieć lokalnie.

- **Szablon**: `docs/env.sample.md` (skopiuj do `.env.dev` i uzupełnij).
- **W DEV nazwy baz mają prefiks `zzz_`** (np. `DEFAULT_DB_NAME=zzz_default`, `MPD_DB_NAME=zzz_MPD`, `MATTERHORN1_DB_NAME=zzz_matterhorn1`).
- Redis w DEV jest w compose i używa hasła `dev_password`.

## Uruchomienie DEV (Docker – zalecane)
### Pierwszy start (Windows)
```powershell
.\scripts\build\build-fast.ps1
docker-compose -f docker-compose.dev.yml up -d
```

### Pierwszy start (Linux/Mac)
```bash
./scripts/build/build-fast.sh
docker-compose -f docker-compose.dev.yml up -d
```

### Dostęp
- **Aplikacja przez Nginx (zalecane)**: `http://localhost:8090/`
- **Bezpośrednio (web)**: `http://localhost:8000/`
- **Flower**: `http://localhost:5555/`

### DEV z ML workerem (opcjonalnie)
```bash
docker-compose -f docker-compose.dev.yml -f docker-compose.dev.ml.yml up -d --build
```

## Najczęstsze komendy (DEV)
```bash
# Logi
docker-compose -f docker-compose.dev.yml logs -f

# Restart web
docker-compose -f docker-compose.dev.yml restart web

# Shell w kontenerze web
docker-compose -f docker-compose.dev.yml exec web bash

# Stop
docker-compose -f docker-compose.dev.yml down
```

## Produkcja (k3s)
Deploy robimy przez GitHub Actions (`Release` → `deploy-vps.yml`), który uruchamia `scripts/k8s-prod/deploy.sh` na k3s. Szczegóły: `docs/K8S_PROD.md`.

> ⚠️ **DEPRECATED**: poniższe skrypty blue‑green (`scripts/deploy/*`) nie są już używane na produkcji — zachowane do wglądu/awaryjnego rollbacku.

```bash
export ENVIRONMENT=prod
./scripts/deploy/deploy-blue-green.sh deploy
./scripts/deploy/deploy-blue-green.sh status
./scripts/deploy/deploy-blue-green.sh rollback
```

### Migracje na produkcji (blue/green, DEPRECATED)
```bash
./scripts/deploy/run-migrations.sh
```

### ML worker na produkcji (blue/green, DEPRECATED)
```bash
docker-compose -f docker-compose.services.yml -f docker-compose.services.ml.yml up -d celery-ml
```

## Dokumentacja
- `docs/QUICK_START.md`
- `docs/DOCKER_QUICK_GUIDE.md`
- `docs/SCRIPTS_GUIDE.md`
- `docs/K8S_PROD.md` (aktualny deploy produkcyjny)
- `docs/BLUE_GREEN_DEPLOYMENT.md` (DEPRECATED)
- **Zewnętrzne API:** `docs/IDOSELL_API.md` (linki do IdoSell: [Getting Started](https://idosell.readme.io/docs/getting-started), [developers](https://www.idosell.com/developers))
