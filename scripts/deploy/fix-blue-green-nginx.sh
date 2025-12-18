#!/bin/bash

# Skrypt do diagnozy i naprawy blue-green deployment z nginx
# Użycie: ./scripts/deploy/fix-blue-green-nginx.sh

set -e

# Kolory
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

echo "=========================================="
echo "🔍 Diagnoza Blue-Green Deployment"
echo "=========================================="
echo ""

# 1. Sprawdź czy jesteśmy w katalogu projektu
if [ ! -f "docker-compose.blue-green.yml" ]; then
    log_error "Nie znaleziono docker-compose.blue-green.yml"
    exit 1
fi

# 2. Sprawdź które kontenery są uruchomione
log_info "Sprawdzanie uruchomionych kontenerów..."
echo ""

# Sprawdź nginx
if docker ps --format '{{.Names}}' | grep -q "nc-nginx-router\|nginx"; then
    NGINX_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E "nc-nginx-router|nginx" | head -1)
    log_success "Nginx znaleziony: $NGINX_CONTAINER"
    docker ps --filter "name=$NGINX_CONTAINER" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
else
    log_warning "Nginx nie jest uruchomiony"
    NGINX_CONTAINER=""
fi
echo ""

# Sprawdź web-blue
if docker ps --format '{{.Names}}' | grep -q "nc-web-blue\|web-blue"; then
    WEB_BLUE=$(docker ps --format '{{.Names}}' | grep -E "nc-web-blue|web-blue" | head -1)
    log_success "web-blue znaleziony: $WEB_BLUE"
    docker ps --filter "name=$WEB_BLUE" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    WEB_BLUE_EXISTS=true
else
    log_warning "web-blue nie jest uruchomiony"
    WEB_BLUE_EXISTS=false
fi
echo ""

# Sprawdź web-green
if docker ps --format '{{.Names}}' | grep -q "nc-web-green\|web-green"; then
    WEB_GREEN=$(docker ps --format '{{.Names}}' | grep -E "nc-web-green|web-green" | head -1)
    log_success "web-green znaleziony: $WEB_GREEN"
    docker ps --filter "name=$WEB_GREEN" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    WEB_GREEN_EXISTS=true
else
    log_warning "web-green nie jest uruchomiony"
    WEB_GREEN_EXISTS=false
fi
echo ""

# Sprawdź web (single)
if docker ps --format '{{.Names}}' | grep -q "^nc_web_1$\|^nc-web$\|web$"; then
    WEB_SINGLE=$(docker ps --format '{{.Names}}' | grep -E "^nc_web_1$|^nc-web$|^web$" | head -1)
    log_warning "Znaleziono pojedynczy kontener web: $WEB_SINGLE"
    log_warning "To może być problem - powinny być web-blue i web-green dla blue-green deployment"
    WEB_SINGLE_EXISTS=true
else
    WEB_SINGLE_EXISTS=false
fi
echo ""

# 3. Sprawdź logi nginx (jeśli istnieje)
if [ ! -z "$NGINX_CONTAINER" ]; then
    log_info "Sprawdzanie logów nginx (ostatnie 20 linii)..."
    docker logs "$NGINX_CONTAINER" --tail 20 2>&1 | grep -E "error|emerg|warn|web-blue|web-green" || echo "Brak błędów w ostatnich logach"
    echo ""
fi

# 4. Sprawdź konfigurację nginx
log_info "Sprawdzanie konfiguracji nginx..."
if [ ! -z "$NGINX_CONTAINER" ]; then
    if docker exec "$NGINX_CONTAINER" nginx -t 2>&1; then
        log_success "Konfiguracja nginx jest poprawna"
    else
        log_error "Konfiguracja nginx zawiera błędy!"
        echo ""
        log_info "Pełne logi testu konfiguracji:"
        docker exec "$NGINX_CONTAINER" nginx -t
        echo ""
    fi
else
    log_warning "Nie można sprawdzić konfiguracji nginx - kontener nie jest uruchomiony"
fi
echo ""

# 5. Sprawdź które pliki są używane
log_info "Sprawdzanie zamontowanych plików nginx..."
if [ ! -z "$NGINX_CONTAINER" ]; then
    docker inspect "$NGINX_CONTAINER" --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}' | grep -E "nginx.*conf|conf.d" || echo "Nie znaleziono informacji o plikach konfiguracyjnych"
fi
echo ""

# 6. Diagnoza i rekomendacje
echo "=========================================="
echo "📋 DIAGNOZA I REKOMENDACJE"
echo "=========================================="
echo ""

if [ "$WEB_BLUE_EXISTS" = false ] && [ "$WEB_GREEN_EXISTS" = false ]; then
    log_error "PROBLEM: Brak kontenerów web-blue i web-green!"
    echo ""
    log_info "Rozwiązanie: Uruchom kontenery blue-green:"
    echo "  docker-compose -f docker-compose.blue-green.yml up -d web-blue web-green"
    echo ""
    
    if [ "$WEB_SINGLE_EXISTS" = true ]; then
        log_warning "Uwaga: Działa pojedynczy kontener 'web' - prawdopodobnie używasz docker-compose.prod.yml zamiast docker-compose.blue-green.yml"
        echo ""
        log_info "Musisz przełączyć się na blue-green deployment:"
        echo "  1. Zatrzymaj obecny nginx i web"
        echo "  2. Uruchom web-blue i web-green"
        echo "  3. Uruchom nginx-router z docker-compose.blue-green.yml"
    fi
    
    echo ""
    read -p "Czy chcesz uruchomić kontenery web-blue i web-green teraz? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Uruchamiam web-blue i web-green..."
        docker-compose -f docker-compose.blue-green.yml up -d web-blue web-green
        log_success "Kontenery uruchomione"
        echo ""
        log_info "Czekam 10 sekund na start kontenerów..."
        sleep 10
        echo ""
    fi
fi

if [ "$WEB_BLUE_EXISTS" = true ] || [ "$WEB_GREEN_EXISTS" = true ]; then
    log_success "Kontenery blue-green istnieją"
    
    # Sprawdź czy nginx używa właściwej konfiguracji
    if [ ! -z "$NGINX_CONTAINER" ]; then
        log_info "Sprawdzanie czy nginx używa nginx-blue-green.conf..."
        
        # Sprawdź czy w kontenerze jest web-blue w konfiguracji
        if docker exec "$NGINX_CONTAINER" cat /etc/nginx/conf.d/default.conf 2>/dev/null | grep -q "web-blue"; then
            log_success "Nginx używa konfiguracji blue-green (zawiera web-blue)"
        else
            log_error "Nginx NIE używa konfiguracji blue-green!"
            log_info "Rozwiązanie: Restart nginx z właściwą konfiguracją"
            echo ""
            read -p "Czy chcesz zrestartować nginx z konfiguracją blue-green? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                log_info "Restartowanie nginx..."
                docker-compose -f docker-compose.blue-green.yml restart nginx-router
                log_success "Nginx zrestartowany"
            fi
        fi
    else
        log_error "Nginx nie jest uruchomiony!"
        echo ""
        read -p "Czy chcesz uruchomić nginx-router teraz? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Uruchamiam nginx-router..."
            docker-compose -f docker-compose.blue-green.yml up -d nginx-router
            log_success "Nginx uruchomiony"
        fi
    fi
fi

echo ""
echo "=========================================="
echo "✅ Diagnoza zakończona"
echo "=========================================="
echo ""
log_info "Przydatne komendy:"
echo "  - Status: docker-compose -f docker-compose.blue-green.yml ps"
echo "  - Logi nginx: docker logs $NGINX_CONTAINER -f"
echo "  - Logi web-blue: docker logs nc-web-blue -f"
echo "  - Logi web-green: docker logs nc-web-green -f"
echo "  - Test: curl http://localhost:8001/nginx-health"
echo ""

