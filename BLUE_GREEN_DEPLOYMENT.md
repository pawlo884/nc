# Blue-Green Deployment - Automatyczne przełączanie

## Architektura

```
Internet → Nginx Proxy Manager (porty 80/443) → nginx-router (wewnętrzny) → web-blue/web-green
```

- **Nginx Proxy Manager**: Reverse proxy z interfejsem webowym, zarządza SSL i domenami
- **nginx-router**: Wewnętrzny router, automatycznie przełącza między blue/green
- **web-blue / web-green**: Dwa identyczne deploymenty aplikacji Django

## Konfiguracja Nginx Proxy Manager

W NPM skonfiguruj proxy host dla swojej domeny:
- **Forward Hostname/IP**: `nc-nginx-router`
- **Forward Port**: `80`
- **Forward Scheme**: `http`

NPM automatycznie znajdzie kontener `nc-nginx-router` przez sieć Docker.

## Automatyczne przełączanie

### 1. Deployment nowej wersji

```bash
cd /home/pawel/apps/nc
./deploy-blue-green.sh
```

Skrypt automatycznie:
1. Wykrywa aktualnie aktywny kolor (blue/green)
2. Deployuje na przeciwny kolor
3. Czeka aż healthcheck przejdzie
4. Przełącza ruch na nowy deployment
5. Zatrzymuje stary kontener po 5 minutach (rollback window)

### 2. Ręczne przełączanie

```bash
cd /home/pawel/apps/nc
./switch-blue-green.sh blue   # Przełącz na blue
./switch-blue-green.sh green  # Przełącz na green
```

### 3. Sprawdzenie statusu

```bash
docker exec nc-nginx-router cat /etc/nginx/state/active_backend.conf
```

## Jak to działa

1. **nginx-router** używa pliku `/etc/nginx/state/active_backend.conf` do określenia aktywnego backendu
2. Skrypt `switch-blue-green.sh` aktualizuje ten plik i przeładowuje nginx (zero-downtime)
3. Skrypt `deploy-blue-green.sh` automatycznie przełącza po deploymencie

## Rollback

Jeśli coś pójdzie nie tak, możesz szybko wrócić:

```bash
./switch-blue-green.sh green  # Wróć do poprzedniego deploymentu
```

Stary kontener jest zatrzymywany dopiero po 5 minutach, więc masz czas na rollback.

## Porty

- **web-blue**: port `8000:8000` (dostępny bezpośrednio dla testów)
- **web-green**: port `8001:8000` (dostępny bezpośrednio dla testów)
- **nginx-router**: tylko wewnętrznie (przez sieć Docker)
- **NPM**: porty `80`, `443` (publiczne), `81` (admin)

## Troubleshooting

### Sprawdź czy router działa:
```bash
docker exec nginx-proxy-manager curl -s http://nc-nginx-router/nginx-health
```

### Sprawdź logi:
```bash
docker logs nc-nginx-router --tail 50
```

### Sprawdź konfigurację:
```bash
docker exec nc-nginx-router nginx -t
```
