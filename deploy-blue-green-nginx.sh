#!/bin/bash

# Skrypt do wdrożenia/restartu blue-green deployment z nginx
# Użycie: ./deploy-blue-green-nginx.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

echo "=========================================="
echo "🚀 Wdrożenie Blue-Green Nginx"
echo "=========================================="
echo ""

# Sprawdź czy plik istnieje
if [ ! -f "docker-compose.blue-green.yml" ]; then
    log_error "Nie znaleziono docker-compose.blue-green.yml"
    exit 1
fi

if [ ! -f "nginx-blue-green.conf" ]; then
    log_error "Nie znaleziono nginx-blue-green.conf"
    exit 1
fi

# Sprawdź czy kontenery web-blue i web-green istnieją
log_info "Sprawdzanie kontenerów web-blue i web-green..."

WEB_BLUE_EXISTS=$(docker ps -a --format '{{.Names}}' | grep -c "nc-web-blue\|web-blue" || echo "0")
WEB_GREEN_EXISTS=$(docker ps -a --format '{{.Names}}' | grep -c "nc-web-green\|web-green" || echo "0")

if [ "$WEB_BLUE_EXISTS" -eq "0" ] || [ "$WEB_GREEN_EXISTS" -eq "0" ]; then
    log_info "Uruchamianie kontenerów web-blue i web-green..."
    docker-compose -f docker-compose.blue-green.yml up -d web-blue web-green
    
    log_info "Czekam 15 sekund na start kontenerów..."
    sleep 15
    
    # Sprawdź czy kontenery działają
    if docker ps --format '{{.Names}}' | grep -q "nc-web-blue\|web-blue"; then
        log_success "web-blue uruchomiony"
    else
        log_error "web-blue nie uruchomił się!"
        docker-compose -f docker-compose.blue-green.yml logs web-blue --tail 50
        exit 1
    fi
    
    if docker ps --format '{{.Names}}' | grep -q "nc-web-green\|web-green"; then
        log_success "web-green uruchomiony"
    else
        log_error "web-green nie uruchomił się!"
        docker-compose -f docker-compose.blue-green.yml logs web-green --tail 50
        exit 1
    fi
else
    log_success "Kontenery web-blue i web-green już istnieją"
    
    # Sprawdź czy działają
    if ! docker ps --format '{{.Names}}' | grep -q "nc-web-blue\|web-blue"; then
        log_info "Restartowanie web-blue..."
        docker-compose -f docker-compose.blue-green.yml restart web-blue
    fi
    
    if ! docker ps --format '{{.Names}}' | grep -q "nc-web-green\|web-green"; then
        log_info "Restartowanie web-green..."
        docker-compose -f docker-compose.blue-green.yml restart web-green
    fi
fi

echo ""

# Sprawdź/uruchom nginx
log_info "Sprawdzanie nginx-router..."

if docker ps --format '{{.Names}}' | grep -q "nc-nginx-router\|nginx-router"; then
    log_success "nginx-router już działa"
    log_info "Restartowanie nginx-router z nową konfiguracją..."
    docker-compose -f docker-compose.blue-green.yml restart nginx-router
else
    log_info "Uruchamiam nginx-router..."
    docker-compose -f docker-compose.blue-green.yml up -d nginx-router
fi

echo ""
log_info "Czekam 5 sekund na start nginx..."
sleep 5

# Sprawdź czy nginx działa
if docker ps --format '{{.Names}}' | grep -q "nc-nginx-router\|nginx-router"; then
    log_success "nginx-router uruchomiony"
    
    # Sprawdź konfigurację
    NGINX_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E "nc-nginx-router|nginx-router" | head -1)
    if docker exec "$NGINX_CONTAINER" nginx -t 2>&1; then
        log_success "Konfiguracja nginx jest poprawna"
    else
        log_error "Błąd w konfiguracji nginx!"
        docker exec "$NGINX_CONTAINER" nginx -t
        exit 1
    fi
    
    # Sprawdź logi
    log_info "Sprawdzanie logów nginx..."
    if docker logs "$NGINX_CONTAINER" --tail 10 2>&1 | grep -q "error\|emerg"; then
        log_error "Znaleziono błędy w logach nginx:"
        docker logs "$NGINX_CONTAINER" --tail 20 | grep -E "error|emerg"
    else
        log_success "Brak błędów w logach nginx"
    fi
else
    log_error "nginx-router nie uruchomił się!"
    docker-compose -f docker-compose.blue-green.yml logs nginx-router --tail 50
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Wdrożenie zakończone"
echo "=========================================="
echo ""
log_info "Status kontenerów:"
docker-compose -f docker-compose.blue-green.yml ps
echo ""
log_info "Testy:"
echo "  - Health check: curl http://localhost:8001/nginx-health"
echo "  - Status: curl http://localhost:80/deployment-status"
echo "  - Logi: docker logs $NGINX_CONTAINER -f"
echo ""

