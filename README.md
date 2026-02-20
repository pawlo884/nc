# NC (nc_project)

Projekt Django + PostgreSQL + Celery/Redis. **Produkcja działa wyłącznie w trybie blue‑green** (`docker-compose.blue-green.yml`).

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
- `src/apps/` – aplikacje Django (matterhorn1, MPD, tabu, …)
- **manage.py** – w katalogu `src/` (uruchomienie: `cd src && python manage.py ...` lub `python src/manage.py ...`)
- `docker/` – pliki Docker (m.in. `docker/docker-entrypoint.sh`, postgres config)
- `scripts/` – skrypty (build/deploy/security/monitoring)
- `docs/` – dokumentacja

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

## Produkcja (tylko blue‑green)
Deploy robimy przez GitHub Actions (`Release` → `deploy-vps.yml`) albo ręcznie na serwerze:

```bash
export ENVIRONMENT=prod
./scripts/deploy/deploy-blue-green.sh deploy
./scripts/deploy/deploy-blue-green.sh status
./scripts/deploy/deploy-blue-green.sh rollback
```

### Migracje na produkcji (blue/green)
```bash
./scripts/deploy/run-migrations.sh
```

### ML worker na produkcji (opcjonalnie)
```bash
docker-compose -f docker-compose.blue-green.yml -f docker-compose.blue-green.ml.yml up -d celery-ml
```

## Dokumentacja
- `docs/QUICK_START.md`
- `docs/DOCKER_QUICK_GUIDE.md`
- `docs/SCRIPTS_GUIDE.md`
- `docs/BLUE_GREEN_DEPLOYMENT.md`
- **Zewnętrzne API:** `docs/IDOSELL_API.md` (linki do IdoSell: [Getting Started](https://idosell.readme.io/docs/getting-started), [developers](https://www.idosell.com/developers))
