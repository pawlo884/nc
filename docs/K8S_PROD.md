# Produkcja na k3s (zamiast blue-green)

Migracja z `docker-compose.blue-green.yml` + `nginx-router` na **k3s + Traefik + 3 repliki + RollingUpdate**.

## Co sie zmienia

| Bylo (Docker prod) | Bedzie (k3s prod) |
|--------------------|-------------------|
| `web-blue` + `web-green` | `Deployment nc-web` × 3 |
| `nginx-router` | Traefik Ingress |
| `deploy-blue-green.sh` | `scripts/k8s-prod/deploy.sh` |
| rollback blue/green | `kubectl rollout undo deployment/nc-web` |

**Bez zmian:** PostgreSQL (`nc-postgres-1`), opcjonalnie Redis Docker (`nc-redis-1`) — dane zostaja.

## Wymagania na VPS

1. **k3s** zainstalowany (`curl -sfL https://get.k3s.io | sh -`)
2. Istniejacy `.env.prod` (jak przy blue-green)
3. `kubectl` + `docker`
4. NPM — po cutover forward na Traefik zamiast `nc-nginx-router`

## PostgreSQL z k3s

Pody musza dojsc do `nc-postgres-1` (Docker). W `.env.prod` ustaw hosty DB na IP hosta VPS, np.:

```env
DEFAULT_DB_HOST=172.17.0.1
TABU_DB_HOST=172.17.0.1
# ... pozostale DB_HOST tak samo
```

(albo IP bridge Docker — sprawdz: `docker inspect nc-postgres-1 | grep IPAddress`)

Porty jak dotychczas (`5432`).

**Hosty DB w `.env.prod`:** ustaw IP hosta VPS (np. `172.17.0.1`), nie `host.k3s.internal` — ten DNS nie dziala na kazdym k3s. Manifesty nadpisuja tylko `REDIS_HOST=redis`; reszta DB_HOST idzie z secretu `nc-env`.

## Redis

Domyslnie manifest uruchamia **Redis w klastrze** (`nc-prod`). Aby zostawic `nc-redis-1` z Docker:

1. Nie aplikuj `redis.yaml` (albo usun po deploy)
2. W `.env.prod` ustaw `REDIS_HOST` na IP/host Dockera i popraw `CELERY_BROKER_URL`

## Instalacja k3s (jednorazowo)

```bash
curl -sfL https://get.k3s.io | sh -
sudo k3s kubectl get nodes

# kubectl dla uzytkownika pawel (bez sudo):
chmod +x scripts/k8s-prod/setup-kubeconfig.sh
./scripts/k8s-prod/setup-kubeconfig.sh
echo 'export KUBECONFIG=$HOME/.kube/config' >> ~/.bashrc
export KUBECONFIG=$HOME/.kube/config
kubectl get pods -n nc-prod
```

Bez setupu: `sudo k3s kubectl get pods -n nc-prod` (dziala od razu).

## Workflow CI (automatyczny deploy)

Po merge → tag (`v*`) → GitHub Actions `deploy-vps.yml`:

1. SSH na VPS
2. `git fetch` + `reset` (bez recznego pull u Ciebie)
3. `create-secret.sh` → `build-image.sh` → `deploy.sh --migrate`

**Jednorazowo na serwerze** (przed pierwszym deployem po merge):

```bash
# k3s
curl -sfL https://get.k3s.io | sh -
./scripts/k8s-prod/setup-kubeconfig.sh
echo 'export KUBECONFIG=$HOME/.kube/config' >> ~/.bashrc

# sudo bez hasla dla build-image (docker save | k3s ctr import) — np. w sudoers dla pawel
# .env.prod — DB_HOST na IP hosta (patrz wyzej), reszta jak dotychczas

# cutover NPM (jednorazowo): nc.sowa.ch -> Traefik :30080 zamiast nc-nginx-router
./scripts/k8s-prod/cutover-from-blue-green.sh
./scripts/k8s-prod/expose-traefik.sh
```

**NPM Proxy Host `nc.sowa.ch`:** Forward → IP serwera (np. `192.168.50.31`), port **30080** (Traefik NodePort). Bez tego NPM dostaje 504.

Kolejne wersje: tylko merge + tag — reszta robi CI.

## Flower (monitoring Celery)

Manifest: `deployments/k8s/nc-prod/flower.yaml` (Deployment + Service + Ingress).

- **Broker:** Redis w klastrze (`redis` w `nc-prod`) — te same workery co `celery-default` / `celery-import`
- **Auth:** `FLOWER_USER` / `FLOWER_PASSWORD` z `.env.prod` (domyslnie admin/flower jak w blue-green)
- **URL:** `https://flower.nc.sowa.ch` — w NPM dodaj Proxy Host -> IP VPS, port 80 (Traefik), host `flower.nc.sowa.ch`
- **Service w k3s:** `nc-flower` (nie `flower` — kolizja zmiennych K8s `FLOWER_PORT`)
- **Lokalnie na serwerze:** `kubectl port-forward -n nc-prod svc/flower 5555:5555`

Po deployu zatrzymaj stary Docker Flower: `docker stop nc-flower`

Rollback:

```bash
kubectl rollout undo deployment/nc-web -n nc-prod
kubectl rollout status deployment/nc-web -n nc-prod
```

## Manifesty

`deployments/k8s/nc-prod/`

## Statyczne pliki / media

Blue-green montowal `/mnt/data2tb/docker/volumes/nc_static_volume`. W k3s obraz ma `collectstatic` z builda (`Dockerfile.prod`). Jesli potrzebujesz wspoldzielonego volume media — dodaj PersistentVolume w kolejnym kroku.

## Workflow GitHub

`deploy-vps.yml` po tagu `v*` uruchamia `scripts/k8s-prod/*.sh` (create-secret, build, deploy --migrate).
Reczny pull na serwerze nie jest potrzebny — robi to SSH w CI.

Srodowisko **test** (`nc-test`) — odlozone; manifesty zostaja w repo na pozniej.

Powiazane: [ZERO_DOWNTIME_DEPLOYMENT.md](ZERO_DOWNTIME_DEPLOYMENT.md), [NGINX_PROXY_MANAGER_SETUP.md](NGINX_PROXY_MANAGER_SETUP.md).
