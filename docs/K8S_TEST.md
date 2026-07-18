# Środowisko test (staging) — k3s

> **Status: odłożone.** Priorytet: produkcja — zobacz [K8S_PROD.md](K8S_PROD.md).

Środowisko **nc-test** na k3s: ten sam wzorzec co docelowy prod (Traefik Ingress, wiele replik, RollingUpdate), **bez blue-green**.

## Łańcuch środowisk

| Środowisko | Gdzie | Deploy | Proxy |
|------------|-------|--------|-------|
| **dev** | laptop, Docker Compose | `docker-compose.dev.yml up` | nginx :8090 |
| **test** | VPS, k3s namespace `nc-test` | `scripts/k8s-test/deploy.sh` | Traefik Ingress |
| **prod** | VPS, Docker blue-green (na razie) | `deploy-blue-green.sh` | nginx-router + NPM |

Docelowo prod przejdzie na ten sam model co test (k3s + repliki).

## Wymagania (VPS)

- k3s z **Traefik** (domyślnie w k3s)
- `kubectl`, `docker`
- PostgreSQL z **osobnymi bazami test** (nie prod!)
- DNS: `nc-test.sowa.ch` → NPM lub bezpośrednio Traefik
- plik `.env.test` (nie commituj — wzór: `docs/env.test.sample.md`)

## Pierwsze wdrożenie

```bash
# 1. Skopiuj i uzupelnij env
cp docs/env.test.sample.md .env.test   # recznie jako .env.test (klucz=wartosc)

# 2. Secret w klastrze
chmod +x scripts/k8s-test/*.sh
./scripts/k8s-test/create-secret.sh

# 3. Obraz + manifesty
./scripts/k8s-test/build-image.sh
./scripts/k8s-test/deploy.sh --migrate
```

Windows (secret tylko):

```powershell
.\scripts\k8s-test\create-secret.ps1
```

## Kolejne deploye

```bash
git pull
./scripts/k8s-test/build-image.sh
./scripts/k8s-test/deploy.sh --migrate   # --migrate gdy sa nowe migracje
```

Bez migracji:

```bash
./scripts/k8s-test/build-image.sh
./scripts/k8s-test/deploy.sh
```

## Architektura

```text
Internet / NPM
      |
 Traefik Ingress (nc-test.sowa.ch)
      |
 Service nc-web (ClusterIP)
      |
 +----+----+
 |         |
Pod 1    Pod 2   (RollingUpdate)
      |
 redis (StatefulSet) + celery-default + celery-import
      |
 PostgreSQL (poza klastrem, host z .env.test)
```

## Manifesty

`deployments/k8s/nc-test/`

| Plik | Zasób |
|------|--------|
| `00-namespace.yaml` | namespace `nc-test` |
| `redis.yaml` | Redis broker |
| `web.yaml` | Django ×2 repliki |
| `celery.yaml` | worker default + import |
| `ingress.yaml` | Traefik → nc-web |
| `migrate-job.yaml` | Job migracji przed rolloutem |

## Settings Django

`DJANGO_SETTINGS_MODULE=core.settings.test` — bazuje na `prod.py`, domena testowa, bazy z `.env.test`.

## Przydatne komendy

```bash
kubectl get all -n nc-test
kubectl logs -f deployment/nc-web -n nc-test
kubectl rollout restart deployment/nc-web -n nc-test
kubectl scale deployment/nc-web --replicas=3 -n nc-test
curl -H "Host: nc-test.sowa.ch" http://<IP-k3s>:80/health/
```

## NPM (opcjonalnie)

Jeśli używasz Nginx Proxy Manager przed k3s:

- **Domain**: `nc-test.sowa.ch`
- **Forward**: IP serwera k3s, port Traefik (80/443)
- **SSL**: Let's Encrypt w NPM

Traefik w k3s routuje po nagłówku `Host: nc-test.sowa.ch` do Service `nc-web`.

Powiązane: [DOCKER_QUICK_GUIDE.md](DOCKER_QUICK_GUIDE.md), [ZERO_DOWNTIME_DEPLOYMENT.md](ZERO_DOWNTIME_DEPLOYMENT.md).
