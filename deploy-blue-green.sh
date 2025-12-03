#!/bin/bash

################################################################################
# Blue-Green Deployment Script
# 
# Ten skrypt wykonuje zero-downtime deployment używając strategii Blue-Green
################################################################################

set -e  # Exit on error

# Kolory do outputu
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funkcje pomocnicze
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Sprawdź który environment jest aktywny
get_active_environment() {
    # Sprawdź który kontener odpowiada (prosty health check)
    if docker exec nc-web-blue curl -sf http://localhost:8000/admin/ > /dev/null 2>&1; then
        if docker inspect nc-web-blue 2>/dev/null | grep -q '"Status": "running"'; then
            echo "blue"
            return
        fi
    fi
    
    if docker exec nc-web-green curl -sf http://localhost:8000/admin/ > /dev/null 2>&1; then
        if docker inspect nc-web-green 2>/dev/null | grep -q '"Status": "running"'; then
            echo "green"
            return
        fi
    fi
    
    # Domyślnie blue
    echo "blue"
}

# Health check
health_check() {
    local environment=$1
    local max_attempts=60  # Zwiększone z 30 do 60 (2 minuty)
    local attempt=1
    
    log_info "🏥 Health check dla ${environment}..."
    log_info "⏳ Czekam na zakończenie migracji..."
    
    while [ $attempt -le $max_attempts ]; do
        # Sprawdź czy kontener jeszcze działa
        if ! docker ps --filter "name=nc-web-${environment}" --filter "status=running" --format '{{.Names}}' | grep -q "nc-web-${environment}"; then
            log_error "❌ Kontener ${environment} nie działa!"
            return 1
        fi
        
        # Sprawdź czy Django odpowiada
        if docker exec nc-web-${environment} curl -sf http://localhost:8000/admin/ > /dev/null 2>&1; then
            log_success "✅ ${environment} jest zdrowy!"
            return 0
        fi
        
        # Pokaż co 10 prób
        if [ $((attempt % 10)) -eq 0 ]; then
            log_info "Próba $attempt/$max_attempts..."
        fi
        sleep 2
        ((attempt++))
    done
    
    log_error "❌ ${environment} nie przeszedł health check po $((max_attempts * 2)) sekundach!"
    log_info "📋 Ostatnie logi kontenera:"
    docker logs nc-web-${environment} --tail 50
    return 1
}

# Przełącz NGINX na nowy environment
switch_nginx() {
    local target=$1
    
    log_info "🔄 Przełączanie NGINX na ${target}..."
    
    # Backup aktualnej konfiguracji
    cp nginx-blue-green.conf nginx-blue-green.conf.backup
    
    # Zmień upstream backend_active
    sed -i.bak "s/server web-blue:8000/server web-${target}:8000/g" nginx-blue-green.conf
    sed -i.bak "s/X-Deployment-Color \"blue\"/X-Deployment-Color \"${target}\"/g" nginx-blue-green.conf
    
    # Przeładuj NGINX
    docker exec nc-nginx-router nginx -t && docker exec nc-nginx-router nginx -s reload
    
    if [ $? -eq 0 ]; then
        log_success "✅ NGINX przełączony na ${target}"
        return 0
    else
        log_error "❌ Błąd podczas przełączania NGINX"
        # Rollback
        mv nginx-blue-green.conf.backup nginx-blue-green.conf
        docker exec nc-nginx-router nginx -s reload
        return 1
    fi
}

# Main deployment function
deploy() {
    log_info "🚀 Rozpoczynam Blue-Green Deployment"
    echo "=================================="
    
    # 1. Określ aktywny environment
    ACTIVE=$(get_active_environment)
    
    if [ "$ACTIVE" = "blue" ]; then
        TARGET="green"
        log_info "🔵 Aktywny: BLUE → 🟢 Deploy na: GREEN"
    else
        TARGET="blue"
        log_info "🟢 Aktywny: GREEN → 🔵 Deploy na: BLUE"
    fi
    
    # 2. Build nowego obrazu
    log_info "🔨 Budowanie nowego obrazu..."
    export DOCKER_BUILDKIT=1
    docker-compose -f docker-compose.blue-green.yml build --no-cache web-${TARGET}
    
    # 3. Zatrzymaj stary kontener target (jeśli istnieje)
    log_info "🛑 Zatrzymywanie starego kontenera ${TARGET}..."
    docker-compose -f docker-compose.blue-green.yml stop web-${TARGET} || true
    
    # 4. Uruchom nowy kontener
    log_info "▶️  Uruchamianie nowego kontenera ${TARGET}..."
    docker-compose -f docker-compose.blue-green.yml up -d web-${TARGET}
    
    # 5. Poczekaj na uruchomienie
    sleep 10
    
    # 6. Health check
    if ! health_check $TARGET; then
        log_error "❌ Deployment failed - health check nie przeszedł"
        log_warning "🔙 Rollback: ${TARGET} nie zostanie aktywowany"
        docker-compose -f docker-compose.blue-green.yml stop web-${TARGET}
        exit 1
    fi
    
    # 7. Przełącz NGINX na nowy environment
    if ! switch_nginx $TARGET; then
        log_error "❌ Nie udało się przełączyć NGINX"
        exit 1
    fi
    
    # 8. Opcjonalnie: poczekaj chwilę i zatrzymaj stary environment
    log_info "⏳ Czekam 30s przed zatrzymaniem ${ACTIVE}..."
    sleep 30
    
    log_info "🛑 Zatrzymywanie starego środowiska ${ACTIVE}..."
    docker-compose -f docker-compose.blue-green.yml stop web-${ACTIVE}
    
    # 9. Sukces!
    log_success "🎉 Deployment zakończony pomyślnie!"
    log_success "✅ Aktywny environment: ${TARGET}"
    log_info "ℹ️  Stary environment (${ACTIVE}) jest zatrzymany i gotowy do rollback"
    
    echo ""
    echo "=================================="
    echo "PODSUMOWANIE:"
    echo "- Poprzedni: ${ACTIVE}"
    echo "- Aktualny:  ${TARGET}"
    echo "- Rollback:  ./rollback-blue-green.sh"
    echo "=================================="
}

# Rollback function
rollback() {
    log_warning "🔙 ROLLBACK - przywracanie poprzedniego environment"
    
    ACTIVE=$(get_active_environment)
    
    if [ "$ACTIVE" = "blue" ]; then
        TARGET="green"
    else
        TARGET="blue"
    fi
    
    log_info "Rollback z ${ACTIVE} na ${TARGET}..."
    
    # Uruchom stary environment
    docker-compose -f docker-compose.blue-green.yml up -d web-${TARGET}
    
    # Health check
    if ! health_check $TARGET; then
        log_error "❌ Rollback failed - ${TARGET} nie jest zdrowy!"
        exit 1
    fi
    
    # Przełącz NGINX
    if ! switch_nginx $TARGET; then
        log_error "❌ Nie udało się przełączyć NGINX"
        exit 1
    fi
    
    log_success "✅ Rollback zakończony - aktywny: ${TARGET}"
}

# Status function
status() {
    echo "=================================="
    echo "BLUE-GREEN DEPLOYMENT STATUS"
    echo "=================================="
    
    # Sprawdź status kontenerów
    echo ""
    echo "🔵 BLUE environment:"
    if docker inspect nc-web-blue 2>/dev/null | grep -q '"Status": "running"'; then
        echo "  Status: ✅ RUNNING"
        if docker exec nc-web-blue curl -sf http://localhost:8000/admin/ > /dev/null 2>&1; then
            echo "  Health: ✅ HEALTHY"
        else
            echo "  Health: ❌ UNHEALTHY"
        fi
    else
        echo "  Status: ⭕ STOPPED"
    fi
    
    echo ""
    echo "🟢 GREEN environment:"
    if docker inspect nc-web-green 2>/dev/null | grep -q '"Status": "running"'; then
        echo "  Status: ✅ RUNNING"
        if docker exec nc-web-green curl -sf http://localhost:8000/admin/ > /dev/null 2>&1; then
            echo "  Health: ✅ HEALTHY"
        else
            echo "  Health: ❌ UNHEALTHY"
        fi
    else
        echo "  Status: ⭕ STOPPED"
    fi
    
    echo ""
    echo "🔀 Active environment: $(get_active_environment)"
    echo "=================================="
}

# Main script
case "$1" in
    deploy)
        deploy
        ;;
    rollback)
        rollback
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|status}"
        echo ""
        echo "Commands:"
        echo "  deploy   - Deploy nowej wersji na nieaktywny environment i przełącz ruch"
        echo "  rollback - Przywróć poprzedni environment"
        echo "  status   - Pokaż status blue/green environments"
        exit 1
        ;;
esac
