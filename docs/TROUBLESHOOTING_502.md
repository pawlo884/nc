# Rozwiązywanie 502 Bad Gateway (nc.sowa.ch)

Gdy Cloudflare pokazuje 502, błąd jest po stronie hosta: **NPM → nc-nginx-router → web**.

## 1. Diagnostyka na serwerze

Uruchom w katalogu projektu (`/home/pawel/apps/nc`):

```bash
# Czy nc-nginx-router i web-green działają?
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "nc-nginx-router|nc-web-green|nc-web-blue"

# Czy nc-nginx-router sięga do backendu (Django)?
docker exec nc-nginx-router wget -qO- --timeout=5 http://nc-web-green:8000/health/ && echo "OK green" || echo "FAIL green"
docker exec nc-nginx-router wget -qO- --timeout=5 http://nc-web-blue:8000/health/  && echo "OK blue"  || echo "FAIL blue"

# Czy nc-nginx-router sam odpowiada?
docker exec nc-nginx-router wget -qO- --timeout=5 http://127.0.0.1/nginx-health && echo "OK router" || echo "FAIL router"
```

- **FAIL green/blue** → problem między nc-nginx-router a kontenerem web (sieć lub web nie działa).
- **OK router, FAIL green i blue** → backend nie działa; uruchom aktywny kontener web (green lub blue).
- Wszystkie **OK** → problem jest między NPM a nc-nginx-router (sieć/DNS).

## 2. NPM i sieć Docker

NPM musi być w **tej samej sieci** co nc-nginx-router: `nginx_proxy_manager_network`.

```bash
# Czy nc-nginx-router jest w sieci NPM?
docker network inspect nginx_proxy_manager_network --format '{{range .Containers}}{{.Name}} {{end}}' | tr ' ' '\n' | grep -E "nc-nginx|nginx"
```

Jeśli **nc-nginx-router** nie ma na liście, dołącz go:

```bash
docker network connect nginx_proxy_manager_network nc-nginx-router
```

Jeśli NPM jest w innym stacku, jego kontener też musi być podłączony do `nginx_proxy_manager_network` (w swoim compose: `networks: - nginx_proxy_manager_network` z `external: true`).

## 3. Hostname w NPM

W Proxy Host dla **nc.sowa.ch**:

- **Forward Hostname / IP:** `nc-nginx-router` (nazwa kontenera)
- **Forward Port:** `80`

Jeśli nadal 502, spróbuj:

- **Forward Hostname:** `nginx-router` (nazwa serwisu z compose),
- albo użyj **opcji przez host** z sekcji 4.

## 4. Opcja: dostęp przez host (bez Docker DNS)

Jeśli rozwiązywanie nazwy `nc-nginx-router` z kontenera NPM nie działa, możesz kierować ruch na port wystawiony na hoście.

W `docker-compose.blue-green.yml` dla serwisu `nginx-router` dodaj (albo odkomentuj):

```yaml
ports:
  - "127.0.0.1:8080:80"
```

Potem:

```bash
docker-compose -f docker-compose/docker-compose.blue-green.yml up -d nginx-router
```

W NPM ustaw:

- **Forward Hostname / IP:** adres IP serwera (np. `192.168.x.x` lub `10.x.x.x`) albo `host.docker.internal` jeśli NPM ma `extra_hosts: host.docker.internal:host-gateway`
- **Forward Port:** `8080`

Przetestuj z serwera: `curl -s http://127.0.0.1:8080/nginx-health` → powinno zwrócić `healthy`.

## 5. Logi

```bash
# Logi nc-nginx-router (błędy proxy do backendu)
docker logs nc-nginx-router --tail 100

# Logi aktywnego web (Django)
docker logs nc-web-green --tail 100
# lub
docker logs nc-web-blue --tail 100
```

W logach nginx szukaj `upstream timed out` lub `no live upstreams` – to potwierdza problem z backendem (web) lub siecią między routerem a web.
