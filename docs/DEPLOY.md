# Deploy produkcji

Jeden stack **docker-compose** na VPS. Bez k3s, bez blue-green (usunięte —
issue #259).

## Model

- Obraz `nc-django-app:latest` — kod + React SPA + `collectstatic` **wypalone**
  w `Dockerfile.prod` (bez bind-mountów, tak jak działały pody k3s).
- Wejście: **NPM** (Nginx Proxy Manager) → `web` (gunicorn + whitenoise dla
  `/static/`). TLS na NPM. Media → MinIO/S3.
- Deploy = `git reset --hard <ref>` → build → migracje → `up -d`. Kilka sekund
  502 na `web` podczas recreate (akceptowalne dla huba katalogowego).

Plik: [`docker-compose/docker-compose.prod.yml`](../docker-compose/docker-compose.prod.yml).
Serwisy: `web`, `celery-fast`, `celery-heavy`, `celery-beat`, `flower`, `redis`,
`migrate` (profil). `celery-ml` (`-Q ml`) = szkielet, nieużywany. Postgres
(`nc-postgres-1`) — **osobno**, profil `shared`, nietykalny.

Workery: **`celery-fast`** (`-Q default`, concurrency 3) — częste/krótkie taski;
**`celery-heavy`** (`-Q import,heavy`, concurrency 2) — `full_import_and_update` +
długie/rzadkie. Patrz `core/celery.py` + `CELERY_TASK_ROUTES` w `settings/base.py`.

## Jak deployować

### Z GitHub Actions (zalecane)

`Actions → Deploy to VPS → Run workflow` → podaj tag lub branch (`ref`).
Tylko ręczne uruchomienie (`workflow_dispatch`) — brak auto-deploy na tagu
(świadome, #224 — `GITHUB_TOKEN` z release'u i tak nie triggeruje workflowów).

### Ręcznie na VPS

```bash
cd /home/pawel/apps/nc
./scripts/deploy-prod.sh v1.44.21     # albo main
```

Skrypt: pobiera ref → `docker compose build` → `--profile migrate run --rm
migrate` → `up -d --remove-orphans` → health check `http://127.0.0.1:8000/health/`.
`--remove-orphans` sprząta kontenery po zmienionych nazwach serwisów.

## Migracje

Serwis `migrate` (profil `migrate`) robi po kolei:

```
migrate --database=default              # apps systemowe + celery beat/results + cache
migrate matterhorn1 --database=matterhorn1
migrate MPD --database=MPD
migrate web_agent --database=web_agent
migrate tabu --database=tabu
migrate mada --database=mada
createcachetable --database=default
```

Routery (`core/db_routers.py::allow_migrate`) pilnują, żeby migracje
aplikacji-luster nie trafiły do `default`.

## NPM

Proxy host `nc.sowa.ch` → Forward: **`nc-web` : 8000** (przez sieć
`nginx_proxy_manager_network`) albo **IP serwera : 8000**. TLS + certyfikat na
NPM. `web` nasłuchuje tylko na `127.0.0.1:8000` + sieci Dockera.

## Rollback

```bash
./scripts/deploy-prod.sh <poprzedni-tag>
```

Migracje wstecznie niezgodne → rollback wymaga też `migrate <app> <numer>` ręcznie.

## Postgres

`nc-postgres-1` zarządzany **osobno** (nie z `docker-compose.prod.yml` — jest
tam tylko za profilem `shared` do `docker compose config`). Zawiera dane
produkcyjne. Backupy / restart poza cyklem deployu aplikacji.
