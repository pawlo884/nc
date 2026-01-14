# Konfiguracja NPM dla plików statycznych

## Problem
Pliki statyczne (CSS/JS) nie ładują się przez Cloudflare → NPM → nginx (port 8090).

## Rozwiązanie

### 1. Konfiguracja Proxy Host w NPM

W NPM dla domeny `nc-dev.sowa.ch`:

**Details Tab:**
- **Domain Names**: `nc-dev.sowa.ch`
- **Scheme**: `http`
- **Forward Hostname/IP**: `localhost` lub IP serwera
- **Forward Port**: `8090` (port nginx)
- **Cache Assets**: ❌ **WYŁĄCZ** (ważne dla dev!)
- **Block Common Exploits**: ✅
- **Websockets Support**: ❌

### 2. Advanced Configuration - Custom Nginx Configuration

W sekcji **Advanced** → **Custom Nginx Configuration** dodaj:

```nginx
# Ważne: NPM przekazuje wszystkie requesty do nginx na porcie 8090
# Nginx obsługuje /static/ bezpośrednio, więc NPM nie powinien cache'ować

# Wyłącz cache dla plików statycznych w NPM
location /static/ {
    proxy_pass http://localhost:8090;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    
    # Cloudflare headers
    proxy_set_header CF-Connecting-IP $http_cf_connecting_ip;
    proxy_set_header CF-Ray $http_cf_ray;
    proxy_set_header CF-Visitor $http_cf_visitor;
    
    # Wyłącz cache w NPM dla plików statycznych
    proxy_cache_bypass 1;
    proxy_no_cache 1;
    
    # Przekaż wszystkie nagłówki z nginx
    proxy_pass_header Server;
    proxy_pass_header X-Served-By;
    proxy_pass_header Access-Control-Allow-Origin;
    
    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    
    # HTTP 1.1
    proxy_http_version 1.1;
    proxy_set_header Connection "";
}

# Główna lokalizacja - przekaż do nginx
location / {
    proxy_pass http://localhost:8090;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    
    # Cloudflare headers
    proxy_set_header CF-Connecting-IP $http_cf_connecting_ip;
    proxy_set_header CF-Ray $http_cf_ray;
    proxy_set_header CF-Visitor $http_cf_visitor;
    
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
}
```

### 3. Ważne ustawienia w NPM

**SSL Tab:**
- **Dla development**: Użyj "None" (bez SSL) - Cloudflare będzie łączyć się przez HTTP
- **Dla produkcji**: Możesz użyć "Request a new SSL Certificate" (Let's Encrypt) lub "Use a Custom Certificate"

**Advanced Tab:**
- **Custom Nginx Configuration**: Wklej konfigurację z powyżej
- **Block Common Exploits**: ✅
- **Websockets Support**: ❌ (chyba że potrzebujesz)

### 3.1. Konfiguracja SSL w Cloudflare (WAŻNE dla błędu 525)

**Błąd 525 "SSL handshake failed"** oznacza, że Cloudflare próbuje połączyć się przez HTTPS z origin, ale origin nie ma SSL.

**Rozwiązanie:**

1. **Opcja A - Flexible SSL (najprostsze dla dev):**
   - W Cloudflare Dashboard → **SSL/TLS** → **Overview**
   - Ustaw **SSL/TLS encryption mode** na **"Flexible"**
   - Cloudflare → HTTPS ✅
   - Cloudflare → Origin: HTTP ✅
   - To pozwala Cloudflare łączyć się przez HTTP z NPM (port 8090)

2. **Opcja B - Full SSL (wymaga SSL w NPM):**
   - W Cloudflare Dashboard → **SSL/TLS** → **Overview**
   - Ustaw **SSL/TLS encryption mode** na **"Full"** (nie "Full (strict)")
   - W NPM → **SSL Tab** → **Request a new SSL Certificate** (Let's Encrypt)
   - Cloudflare → HTTPS ✅
   - Cloudflare → Origin: HTTPS ✅

**Dla development zalecam Opcję A (Flexible)** - najprostsze i wystarczające.

### 4. Sprawdzenie konfiguracji

Po zapisaniu konfiguracji w NPM:

1. **Sprawdź czy NPM przekazuje requesty do nginx:**
   ```bash
   curl -I http://localhost:8090/static/admin/css/base.css
   ```
   Powinno zwrócić `200 OK` z nagłówkiem `X-Served-By: nginx`

2. **Sprawdź przez NPM:**
   ```bash
   curl -I http://nc-dev.sowa.ch/static/admin/css/base.css
   ```
   Powinno zwrócić `200 OK` z nagłówkiem `X-Served-By: nginx`

3. **Sprawdź przez Cloudflare:**
   ```bash
   curl -k -I https://nc-dev.sowa.ch/static/admin/css/base.css
   ```
   Powinno zwrócić `200 OK` z nagłówkiem `X-Served-By: nginx`

### 5. Rozwiązywanie problemów

**Problem: Error 525 - SSL handshake failed**
- ✅ **Najczęstsza przyczyna**: Cloudflare ma SSL/TLS mode ustawiony na "Full" lub "Full (strict)", ale NPM nie ma SSL
- **Rozwiązanie**: W Cloudflare → SSL/TLS → Overview → ustaw na **"Flexible"**
- Albo skonfiguruj SSL w NPM (Let's Encrypt) i ustaw Cloudflare na "Full"
- Sprawdź czy NPM nasłuchuje na porcie 8090 (HTTP, nie HTTPS)

**Problem: 404 Not Found**
- Sprawdź czy `Forward Port` w NPM to `8090`
- Sprawdź czy nginx działa: `docker ps | grep nginx`
- Sprawdź logi NPM: `docker logs <nazwa-kontenera-npm>`
- Sprawdź czy pliki są w `/app/staticfiles/`: `docker exec docker-compose-nginx-1 ls -la /app/staticfiles/admin/css/`

**Problem: Cache w NPM**
- Wyłącz `Cache Assets` w Details Tab
- Dodaj `proxy_cache_bypass 1;` i `proxy_no_cache 1;` w location /static/

**Problem: Brak nagłówków CORS**
- Upewnij się, że nginx dodaje nagłówki CORS (już skonfigurowane)
- Sprawdź czy NPM nie usuwa nagłówków - dodaj `proxy_pass_header` w konfiguracji

**Problem: Cloudflare cache'uje 404**
- Wyczyść cache w Cloudflare: Dashboard → Caching → Purge Everything
- Ustaw Page Rule dla `/static/*`: Cache Level = Bypass (tymczasowo)

### 6. Alternatywne rozwiązanie - bezpośrednie przekierowanie w NPM

Jeśli powyższe nie działa, możesz skonfigurować NPM tak, aby `/static/` szedł bezpośrednio do nginx, a reszta do Django:

```nginx
# W Advanced → Custom Nginx Configuration
location /static/ {
    # Bezpośrednio do nginx (port 8090)
    proxy_pass http://localhost:8090/static/;
    proxy_set_header Host $host;
    proxy_cache_bypass 1;
    proxy_no_cache 1;
}

location / {
    # Reszta do Django przez nginx
    proxy_pass http://localhost:8090;
    proxy_set_header Host $host;
}
```

## Podsumowanie

1. ✅ NPM → nginx (port 8090) dla wszystkich requestów
2. ✅ Nginx obsługuje `/static/` bezpośrednio
3. ✅ Wyłącz cache w NPM dla `/static/`
4. ✅ Przekaż wszystkie nagłówki z nginx (w tym CORS)
5. ✅ Wyczyść cache w Cloudflare

Po zastosowaniu tych ustawień pliki statyczne powinny działać poprawnie przez Cloudflare → NPM → nginx.
