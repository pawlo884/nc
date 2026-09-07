# Deploy produkcji

> Stan: **Faza 0** wdrożona (pliki gotowe), cutover z k3s jeszcze **nie
> wykonany** — patrz [issue #259](https://github.com/pawlo884/nc/issues/259).
> Do czasu cutoveru prod nadal działa: `web` na k3s + reszta na
> `docker-compose.services.yml`.

## Model docelowy

Jeden stack **docker-compose** na VPS, bez k3s, bez blue-green.

- Obraz `nc-django-app:latest` — kod + React SPA + `collectstatic` **wypalone**
  w `Dockerfile.prod` (bez bind-mountów).
- Wejście: **NPM** (Nginx Proxy Manager) → `web` (gunicorn + whitenoise dla
  `/static/`). TLS na NPM. Media → MinIO/S3.
- Deploy = `git reset --hard <ref>` → build → migracje → `up -d`. Kilka sekund
  502 na `web` podczas recreate (akceptowalne dla huba katalogowego).

Plik: [`docker-compose/docker-compose.prod.yml`](../docker-compose/docker-compose.prod.yml).
Serwisy: `web`, `celery-default`, `celery-import`, `celery-beat`, `flower`,
`redis`, `migrate` (profil). Postgres (`nc-postgres-1`) — **osobno**, profil
`shared`, nietykalny.

## Jak deployować

### Z GitHub Actions (zalecane)

`Actions → Deploy to VPS → Run workflow` → podaj tag lub branch (`ref`).
Tylko ręczne uruchomienie (`workflow_dispatch`) — brak auto-deploy na tagu
(świadome, #224).

### Ręcznie na VPS

```bash
cd /home/pawel/apps/nc
./scripts/deploy-prod.sh v1.44.20     # albo main
```

Skrypt: pobiera ref → `docker compose build` → `--profile migrate run --rm
migrate` → `up -d --remove-orphans` → health check `http://127.0.0.1:8000/health/`.

## Migracje

Serwis `migrate` (profil `migrate`) robi po kolei:

```
migrate --database=default              # apps systemowe + celery beat/results + cache
migrate matterhorn1 --database=matterhorn1
migrate MPD --database=MPD
migrate web_agent --database=web_agent
migrate tabu --database=tabu
migrate mada --database=mada            # było POMIJANE w k3s migrate-job
createcachetable --database=default
```

Routery (`core/db_routers.py`) pilnują, żeby migracje aplikacji-luster nie
trafiły do `default`. (Stary `migrate-job.yaml` miał dodatkowy hack
`DELETE FROM django_migrations` — usunięty, to była jednorazowa naprawa
historycznego bałaganu, nie rzecz na każdy deploy.)

## Rollback

```bash
./scripts/deploy-prod.sh <poprzedni-tag>
```

Migracje wstecznie niezgodne → rollback wymaga też `migrate <app> <numer>` ręcznie.

## Cutover z k3s (jednorazowo, Faza 1 #259)

1. Na VPS: `git pull` (żeby był `docker-compose.prod.yml`) → `docker compose -f docker-compose/docker-compose.services.yml down web-blue web-green nginx-router` (usuń martwe blue-green).
2. `./scripts/deploy-prod.sh main` — postawi `web` + zaadoptuje redis/celery/flower do stacka `prod`.
3. **NPM:** przełącz `nc.sowa.ch` z `IP:80` (Traefik) na `IP:8000` (albo Forward Hostname `nc-web`, port `8000`).
4. Weryfikacja end-to-end (admin, `/mpd-app/`, eksport XML, API).
5. `kubectl scale deployment/nc-web -n nc-prod --replicas=0` (manifesty zostają na rollback).
6. Obserwacja ~1 dzień → Faza 2: `kubectl delete namespace nc-prod`, `k3s-uninstall.sh`, usunięcie `deployments/k8s/`, `scripts/k8s-prod/`, `scripts/deploy/`.

**Rollback cutoveru:** NPM z powrotem na `:80` + `kubectl scale ... --replicas=3`.
