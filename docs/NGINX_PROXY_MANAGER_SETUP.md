# Konfiguracja Nginx Proxy Manager dla produkcji

## 🎯 Cel

Skonfigurować Nginx Proxy Manager (NPM) do automatycznego zarządzania blue-green deployment bez ręcznego przełączania kontenerów przy każdym deploymencie.

## ✨ Rozwiązanie

Używamy **load balancing z backup** - NPM automatycznie:
- Używa primary kontenera (`nc-web-blue`) gdy działa
- Przełącza się na backup (`nc-web-green`) gdy primary nie odpowiada
- Wraca na primary gdy znów zacznie działać

**Nie musisz ręcznie zmieniać konfiguracji przy deploymencie!** 🎉

## 📋 Wymagania

- Nginx Proxy Manager (NPM) zainstalowany i działający
- Kontenery Django (`nc-web-blue` i `nc-web-green`) działające w sieci Docker
- Port 8001 dostępny z zewnątrz (opcjonalnie)
- Kontenery NPM i Django w tej samej sieci Docker

## 🔧 Konfiguracja Proxy Host dla portu 8001

### Krok 1: Utwórz Proxy Host w NPM

1. Zaloguj się do interfejsu Nginx Proxy Manager (zwykle `http://IP:81`)
2. Przejdź do **Proxy Hosts** → **Add Proxy Host**

### Krok 2: Podstawowa konfiguracja - Load Balancing dla Blue-Green

**⚠️ WAŻNE**: Dla blue-green deployment użyjemy load balancing, żeby NPM automatycznie przełączał się między kontenerami.

**Details Tab:**
- **Domain Names**: `212.127.93.27` (lub zostaw puste dla IP)
- **Scheme**: `http`
- **Forward Hostname/IP**: `nc-web-blue` (tymczasowo - zmienimy to w Advanced)
- **Forward Port**: `8000`
- **Cache Assets**: ✅ (opcjonalnie)
- **Block Common Exploits**: ✅
- **Websockets Support**: ❌ (chyba że potrzebujesz WebSockets)

### Krok 3: Konfiguracja Advanced - Load Balancing + Custom Headers

Przejdź do zakładki **Advanced** i w sekcji **Custom Nginx Configuration** dodaj:

```nginx
# Upstream dla Blue-Green deployment z automatycznym failover
upstream django_backend {
    # Primary - aktywny kontener (domyślnie blue)
    server nc-web-blue:8000 max_fails=3 fail_timeout=30s;
    
    # Backup - standby kontener (domyślnie green)
    # Nginx automatycznie przełączy się na green jeśli blue nie działa
    server nc-web-green:8000 max_fails=3 fail_timeout=30s backup;
}

# Custom headers dla Django
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-Port $server_port;

# Timeouts
proxy_connect_timeout 60s;
proxy_send_timeout 300s;
proxy_read_timeout 300s;

# HTTP 1.1
proxy_http_version 1.1;
proxy_set_header Connection "";

# Buffering
proxy_buffering on;
proxy_buffer_size 4k;
proxy_buffers 8 4k;
proxy_busy_buffers_size 8k;

# Użyj upstream zamiast bezpośredniego proxy_pass
# (to zostanie dodane w location block poniżej)
```

**WAŻNE**: W sekcji **Custom Nginx Configuration** musisz też nadpisać location block:

```nginx
location / {
    proxy_pass http://django_backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;
    
    proxy_connect_timeout 60s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
}
```

**Alternatywa - Load Balancing z równomiernym rozłożeniem** (jeśli chcesz używać obu kontenerów jednocześnie):

```nginx
# Upstream z równomiernym rozłożeniem (round-robin)
upstream django_backend {
    least_conn;  # Użyj kontenera z najmniejszą liczbą połączeń
    server nc-web-blue:8000 max_fails=3 fail_timeout=30s;
    server nc-web-green:8000 max_fails=3 fail_timeout=30s;
}
```

**Uwaga**: Jeśli używasz równomiernego rozłożenia, oba kontenery muszą mieć tę samą wersję aplikacji!

**LUB** użyj sekcji **Custom Headers** w NPM (jeśli dostępna):

| Header Name | Header Value |
|------------|--------------|
| `X-Forwarded-Host` | `$host` |
| `X-Forwarded-Port` | `$server_port` |
| `X-Real-IP` | `$remote_addr` |
| `X-Forwarded-For` | `$proxy_add_x_forwarded_for` |
| `X-Forwarded-Proto` | `$scheme` |

### Krok 5: Health Checks (zalecane)

Dodaj health checks w **Advanced** → **Custom Nginx Configuration**:

```nginx
# Health check endpoint dla upstream
upstream django_backend {
    server nc-web-blue:8000 max_fails=3 fail_timeout=30s;
    server nc-web-green:8000 max_fails=3 fail_timeout=30s backup;
    
    # Health check (jeśli nginx ma moduł health check)
    # keepalive 32;
}
```

**Lub użyj health check przez location:**
```nginx
location /health {
    access_log off;
    proxy_pass http://django_backend/admin/;
    proxy_set_header Host $host;
}
```

### Krok 6: Konfiguracja SSL (opcjonalnie)

Jeśli używasz HTTPS:
- **SSL Certificate**: Wybierz certyfikat lub użyj Let's Encrypt
- **Force SSL**: ✅ (zalecane dla produkcji)
- **HTTP/2 Support**: ✅

### Krok 4: Port forwarding dla portu 8001

Jeśli chcesz używać portu 8001 zamiast domyślnego 80:

**Opcja A - Streams (jeśli NPM obsługuje):**
1. Przejdź do **Streams** w NPM
2. Utwórz stream:
   - **Listen Port**: `8001`
   - **Forward Host**: `nc-web-blue` (lub użyj upstream `django_backend` jeśli możliwe)
   - **Forward Port**: `8000`

**Opcja B - Drugi Proxy Host:**
1. Utwórz kolejny Proxy Host w NPM
2. Użyj tej samej konfiguracji co pierwszy
3. W **Details** ustaw:
   - **Domain Names**: `212.127.93.27:8001` (lub puste)
   - **Forward Hostname/IP**: `nc-web-blue` (zostanie nadpisane przez upstream w Advanced)
4. W **Advanced** użyj tej samej konfiguracji upstream z `django_backend`

**Opcja C - Custom Port w tym samym Proxy Host:**
W **Advanced** → **Custom Nginx Configuration** dodaj:

```nginx
# Server block dla portu 8001
server {
    listen 8001;
    server_name _;
    
    location / {
        proxy_pass http://django_backend;
        # ... reszta konfiguracji jak wyżej
    }
}
```

**Uwaga**: NPM może nie obsługiwać custom portów w jednym Proxy Host - wtedy użyj Opcji B.

## 🔍 Weryfikacja konfiguracji

### Sprawdź czy kontenery są w tej samej sieci Docker

```bash
# Sprawdź sieć kontenera Django
docker inspect nc-web-blue | grep -A 10 "Networks"

# Sprawdź sieć kontenera NPM
docker inspect <nazwa-kontenera-npm> | grep -A 10 "Networks"
```

**Ważne**: Kontenery muszą być w tej samej sieci Docker! Jeśli nie są:
1. Dodaj kontener NPM do sieci `nc_network`:
   ```bash
   docker network connect nc_network <nazwa-kontenera-npm>
   ```

2. Lub dodaj kontener Django do sieci NPM:
   ```bash
   docker network connect <sieć-npm> nc-web-blue
   ```

### Test połączenia

```bash
# Z zewnątrz
curl -v http://212.127.93.27:8001/admin/

# Z wewnątrz serwera
curl -v http://localhost:8001/admin/
```

## ⚠️ Troubleshooting

### Problem: "502 Bad Gateway"

**Rozwiązanie:**
1. Sprawdź czy kontener Django działa:
   ```bash
   docker ps | grep nc-web
   ```

2. Sprawdź logi Django:
   ```bash
   docker logs nc-web-blue
   ```

3. Sprawdź czy kontenery są w tej samej sieci:
   ```bash
   docker network inspect nc_network
   ```

### Problem: "Invalid HTTP_HOST header"

**Rozwiązanie:**
- Upewnij się, że w `nc/settings/prod.py` masz:
  ```python
  ALLOWED_HOSTS = ['212.127.93.27', ...]
  ```

### Problem: "CSRF verification failed"

**Rozwiązanie:**
- Upewnij się, że w `nc/settings/prod.py` masz:
  ```python
  CSRF_TRUSTED_ORIGINS = [
      'http://212.127.93.27:8001',
      ...
  ]
  ```

### Problem: Nagłówki nie są przekazywane

**Rozwiązanie:**
- Sprawdź konfigurację Custom Headers w NPM
- Upewnij się, że używasz Advanced → Custom Nginx Configuration
- Sprawdź logi NPM:
  ```bash
  docker logs <nazwa-kontenera-npm>
  ```

## 🔄 Automatyczne przełączanie Blue/Green

Z konfiguracją load balancing z `backup` (jak w Kroku 3), NPM automatycznie:

1. **Używa primary kontenera** (`nc-web-blue`) gdy działa
2. **Automatycznie przełącza się na backup** (`nc-web-green`) gdy primary nie odpowiada
3. **Wraca na primary** gdy znów zacznie działać

### Ręczne przełączanie (jeśli potrzebne)

Jeśli chcesz ręcznie zmienić który kontener jest primary, edytuj w NPM → Advanced → Custom Nginx Configuration:

**Aby użyć Green jako primary:**
```nginx
upstream django_backend {
    server nc-web-green:8000 max_fails=3 fail_timeout=30s;
    server nc-web-blue:8000 max_fails=3 fail_timeout=30s backup;
}
```

**Aby użyć Blue jako primary:**
```nginx
upstream django_backend {
    server nc-web-blue:8000 max_fails=3 fail_timeout=30s;
    server nc-web-green:8000 max_fails=3 fail_timeout=30s backup;
}
```

### Integracja z deploy script

Twój skrypt `deploy-blue-green.sh` może automatycznie aktualizować konfigurację NPM przez API (jeśli NPM ma API) lub przez edycję pliku konfiguracyjnego NPM.

**Przykład skryptu do aktualizacji NPM:**
```bash
# W deploy-blue-green.sh, po przełączeniu kontenera:
# Zaktualizuj upstream w NPM (jeśli masz dostęp do plików NPM)
# Lub użyj NPM API (jeśli dostępne)
```

## 📝 Przykładowa konfiguracja dla portu 80

Jeśli chcesz też skonfigurować port 80:

1. Utwórz kolejny Proxy Host
2. **Domain Names**: `212.127.93.27`
3. **Forward Hostname/IP**: `nc-web-blue`
4. **Forward Port**: `8000`
5. Dodaj te same Custom Headers jak dla portu 8001

## 🔐 Bezpieczeństwo

- ✅ Używaj HTTPS w produkcji (Let's Encrypt przez NPM)
- ✅ Włącz "Block Common Exploits"
- ✅ Skonfiguruj rate limiting w NPM (jeśli dostępne)
- ✅ Regularnie aktualizuj NPM

## 📋 Przykładowa pełna konfiguracja dla NPM

Oto kompletna konfiguracja do wklejenia w **Advanced** → **Custom Nginx Configuration**:

```nginx
# Upstream dla Blue-Green deployment
upstream django_backend {
    # Primary kontener (zmień kolejność aby przełączyć primary/backup)
    server nc-web-blue:8000 max_fails=3 fail_timeout=30s;
    
    # Backup kontener - automatycznie użyty gdy primary nie działa
    server nc-web-green:8000 max_fails=3 fail_timeout=30s backup;
}

# Nadpisz location block
location / {
    proxy_pass http://django_backend;
    
    # Headers dla Django
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;
    
    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    
    # HTTP 1.1
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    
    # Buffering
    proxy_buffering on;
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;
    proxy_busy_buffers_size 8k;
    
    # Error handling
    proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
    proxy_next_upstream_tries 2;
    proxy_next_upstream_timeout 10s;
}
```

## 📚 Dodatkowe zasoby

- [Nginx Proxy Manager Documentation](https://nginxproxymanager.com/guide/)
- [Django ALLOWED_HOSTS](https://docs.djangoproject.com/en/stable/ref/settings/#allowed-hosts)
- [Django CSRF_TRUSTED_ORIGINS](https://docs.djangoproject.com/en/stable/ref/settings/#csrf-trusted-origins)
- [Nginx Upstream Module](https://nginx.org/en/docs/http/ngx_http_upstream_module.html)
