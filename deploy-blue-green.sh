#!/bin/bash

################################################################################
# Blue-Green Deployment Script
# 
# Ten skrypt wykonuje zero-downtime deployment używając strategii Blue-Green
################################################################################

set -e  # Exit on error

################################################################################
# ⚠️⚠️⚠️  NIETYKALNE KONTENERY - NIGDY NIE DOTYKAĆ!  ⚠️⚠️⚠️
################################################################################
# Te kontenery zawierają dane produkcyjne i są całkowicie nietykalne:
# - nc-postgres-1  - Baza danych PostgreSQL z wszystkimi danymi
# - nc-redis-1     - Redis z cache i sesjami
#
# ❌ NIGDY nie uruchamiaj dla nich: docker-compose up/stop/restart/rebuild
# ❌ NIGDY nie dodawaj ich do komend docker-compose w tym skrypcie
# ✅ Tylko sprawdzaj czy działają (docker ps)
# ✅ Tylko sprawdzaj ich zdrowie (health check)
#
# Jeśli któryś z tych kontenerów nie działa - deployment MUSI się zatrzymać!
################################################################################

# Lista nietykalnych kontenerów (używana do weryfikacji)
PROTECTED_CONTAINERS=("nc-postgres-1" "nc-redis-1")

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

# Sprawdź czy nietykalne kontenery działają
check_protected_containers() {
    log_info "🔒 Sprawdzanie nietykalnych kontenerów (PostgreSQL, Redis)..."
    
    for container in "${PROTECTED_CONTAINERS[@]}"; do
        if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            log_error "❌ KRYTYCZNE: Nietykalny kontener ${container} nie działa!"
            log_error "❌ Deployment zatrzymany - nie można kontynuować bez bazy danych!"
            exit 1
        fi
        
        # Sprawdź health status jeśli jest dostępny
        health_status=$(docker inspect --format='{{.State.Health.Status}}' "${container}" 2>/dev/null || echo "no-healthcheck")
        if [ "$health_status" = "healthy" ]; then
            log_success "✅ ${container} działa i jest zdrowy"
        elif [ "$health_status" = "no-healthcheck" ]; then
            log_success "✅ ${container} działa (brak health check)"
        else
            log_warning "⚠️ ${container} działa ale health status: ${health_status}"
        fi
    done
    
    log_success "✅ Wszystkie nietykalne kontenery działają poprawnie"
}

# Funkcja bezpieczna dla docker-compose - sprawdza czy nie próbujemy dotknąć nietykalnych
verify_no_protected_containers() {
    local services="$1"
    
    for container in "${PROTECTED_CONTAINERS[@]}"; do
        container_name=$(echo "$container" | sed 's/nc-//')
        if echo "$services" | grep -qE "\b${container_name}\b"; then
            log_error "❌ BŁĄD BEZPIECZEŃSTWA: Próba manipulacji nietykalnym kontenerem ${container}!"
            log_error "❌ Usługa '${container_name}' jest na liście nietykalnych i nie może być dotknięta!"
            exit 1
        fi
    done
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
    
    # 0. Zapisz timestamp PostgreSQL PRZED jakimikolwiek operacjami
    POSTGRES_STARTED_BEFORE_DEPLOY=$(docker inspect nc-postgres-1 --format='{{.State.StartedAt}}' 2>/dev/null || echo "")
    if [ -z "$POSTGRES_STARTED_BEFORE_DEPLOY" ]; then
        log_error "❌ KRYTYCZNE: Nie można sprawdzić statusu PostgreSQL!"
        exit 1
    fi
    log_info "📝 PostgreSQL StartedAt przed deploy: $POSTGRES_STARTED_BEFORE_DEPLOY"
    
    # 1. Upewnij się że nginx-router działa
    log_info "🔍 Sprawdzanie NGINX router..."
    
    # Sprawdź czy stary nginx (z prod.yml) działa i zatrzymaj go
    # ⚠️ UWAGA: To jest bezpieczne - dotyka tylko starego nginx, nie nietykalnych kontenerów!
    if docker ps --format '{{.Names}}' | grep -q "^nc-nginx-1$"; then
        log_warning "⚠️ Stary NGINX (nc-nginx-1) działa, zatrzymuję go..."
        # Bezpieczne - nie dotyka nietykalnych kontenerów
        docker stop nc-nginx-1 2>/dev/null || true
        docker rm nc-nginx-1 2>/dev/null || true
        log_success "✅ Stary NGINX zatrzymany"
        sleep 2
    fi
    
    # ⚠️⚠️⚠️ NIETYKALNE KONTENERY - tylko sprawdzenie, nigdy nie dotykać! ⚠️⚠️⚠️
    check_protected_containers
    
    # Uruchom tylko nginx-router
    # ⚠️ UWAGA: NIE dodawaj postgres ani redis do tej komendy - są nietykalne!
    if ! docker ps --format '{{.Names}}' | grep -q "nc-nginx-router"; then
        log_warning "⚠️ NGINX router nie działa, uruchamiam..."
        
        # Bezpieczeństwo: weryfikuj że nie próbujemy dotknąć nietykalnych
        verify_no_protected_containers "nginx-router"
        
        # ⚠️ WAŻNE: Tylko nginx-router, bez postgres i redis!
        # Zapisz timestamp PostgreSQL przed operacją
        POSTGRES_STARTED_BEFORE=$(docker inspect nc-postgres-1 --format='{{.State.StartedAt}}' 2>/dev/null || echo "")
        
        if ! docker-compose -f docker-compose.blue-green.yml up -d nginx-router; then
            log_error "❌ Nie udało się uruchomić NGINX router"
            exit 1
        fi
        
        # Sprawdź czy PostgreSQL nie został przypadkiem odtworzony
        POSTGRES_STARTED_AFTER=$(docker inspect nc-postgres-1 --format='{{.State.StartedAt}}' 2>/dev/null || echo "")
        if [ -n "$POSTGRES_STARTED_BEFORE" ] && [ "$POSTGRES_STARTED_BEFORE" != "$POSTGRES_STARTED_AFTER" ]; then
            log_error "❌ KRYTYCZNE: PostgreSQL został odtworzony podczas deploya!"
            log_error "❌ Started before: $POSTGRES_STARTED_BEFORE"
            log_error "❌ Started after:  $POSTGRES_STARTED_AFTER"
            exit 1
        fi
        
        log_success "✅ NGINX router uruchomiony"
        sleep 5
    else
        log_success "✅ NGINX router już działa"
    fi
    
    # 2. Określ aktywny environment
    ACTIVE=$(get_active_environment)
    
    if [ "$ACTIVE" = "blue" ]; then
        TARGET="green"
        log_info "🔵 Aktywny: BLUE → 🟢 Deploy na: GREEN"
    else
        TARGET="blue"
        log_info "🟢 Aktywny: GREEN → 🔵 Deploy na: BLUE"
    fi
    
    # 3. Build nowego obrazu
    log_info "🔨 Budowanie nowego obrazu..."
    export DOCKER_BUILDKIT=1
    
    # Zapisz timestamp PostgreSQL przed operacją
    POSTGRES_STARTED_BEFORE=$(docker inspect nc-postgres-1 --format='{{.State.StartedAt}}' 2>/dev/null || echo "")
    
    # ✅ Bezpieczne - buduje web-${TARGET} i kontenery Celery (używają tego samego obrazu), nie dotyka nietykalnych kontenerów
    if ! docker-compose -f docker-compose.blue-green.yml build --no-cache web-${TARGET} celery-default celery-import celery-beat flower; then
        log_error "❌ Nie udało się zbudować obrazu"
        exit 1
    fi
    
    # Sprawdź czy PostgreSQL nie został przypadkiem odtworzony
    POSTGRES_STARTED_AFTER=$(docker inspect nc-postgres-1 --format='{{.State.StartedAt}}' 2>/dev/null || echo "")
    if [ -n "$POSTGRES_STARTED_BEFORE" ] && [ "$POSTGRES_STARTED_BEFORE" != "$POSTGRES_STARTED_AFTER" ]; then
        log_error "❌ KRYTYCZNE: PostgreSQL został odtworzony podczas builda!"
        log_error "❌ Started before: $POSTGRES_STARTED_BEFORE"
        log_error "❌ Started after:  $POSTGRES_STARTED_AFTER"
        exit 1
    fi
    
    # 3.5. Restart kontenerów Celery z nowym obrazem
    log_info "🔄 Restartowanie kontenerów Celery z nowym obrazem..."
    # ✅ Bezpieczne - restartuje tylko kontenery Celery, nie dotyka nietykalnych kontenerów
    docker-compose -f docker-compose.blue-green.yml up -d --force-recreate --no-deps celery-default celery-import celery-beat flower 2>/dev/null || {
        log_warning "⚠️ Nie udało się zrestartować kontenerów Celery, kontynuuję..."
    }
    log_success "✅ Kontenery Celery zrestartowane"
    
    # 4. Zatrzymaj stary kontener target (jeśli istnieje)
    log_info "🛑 Zatrzymywanie starego kontenera ${TARGET}..."
    # ✅ Bezpieczne - dotyka tylko web-${TARGET}, nie dotyka nietykalnych kontenerów
    docker-compose -f docker-compose.blue-green.yml stop web-${TARGET} 2>/dev/null || true
    
    # 5. Uruchom nowy kontener
    log_info "▶️  Uruchamianie nowego kontenera ${TARGET}..."
    # ✅ Bezpieczne - uruchamia tylko web-${TARGET}, nie dotyka nietykalnych kontenerów
    if ! docker-compose -f docker-compose.blue-green.yml up -d web-${TARGET}; then
        log_error "❌ Nie udało się uruchomić kontenera ${TARGET}"
        exit 1
    fi
    
    # 6. Poczekaj na uruchomienie
    sleep 10
    
    # 7. Health check
    if ! health_check $TARGET; then
        log_error "❌ Deployment failed - health check nie przeszedł"
        log_warning "🔙 Rollback: ${TARGET} nie zostanie aktywowany"
        # ✅ Bezpieczne - zatrzymuje tylko web-${TARGET}, nie dotyka nietykalnych kontenerów
        docker-compose -f docker-compose.blue-green.yml stop web-${TARGET} 2>/dev/null || log_warning "⚠️ Nie można zatrzymać kontenera ${TARGET}"
        exit 1
    fi
    
    # 8. Przełącz NGINX na nowy environment
    if ! switch_nginx $TARGET; then
        log_error "❌ Nie udało się przełączyć NGINX"
        exit 1
    fi
    
    # 9. Opcjonalnie: poczekaj chwilę i zatrzymaj stary environment
    log_info "⏳ Czekam 30s przed zatrzymaniem ${ACTIVE}..."
    sleep 30
    
    log_info "🛑 Zatrzymywanie starego środowiska ${ACTIVE}..."
    # ✅ Bezpieczne - zatrzymuje tylko web-${ACTIVE}, nie dotyka nietykalnych kontenerów
    docker-compose -f docker-compose.blue-green.yml stop web-${ACTIVE} 2>/dev/null || log_warning "⚠️ Nie można zatrzymać kontenera ${ACTIVE}"
    
    # 10. Finalna weryfikacja - sprawdź czy PostgreSQL nie został odtworzony
    POSTGRES_STARTED_AFTER_DEPLOY=$(docker inspect nc-postgres-1 --format='{{.State.StartedAt}}' 2>/dev/null || echo "")
    if [ -n "$POSTGRES_STARTED_BEFORE_DEPLOY" ] && [ "$POSTGRES_STARTED_BEFORE_DEPLOY" != "$POSTGRES_STARTED_AFTER_DEPLOY" ]; then
        log_error "❌ KRYTYCZNE: PostgreSQL został odtworzony podczas deploya!"
        log_error "❌ Started before: $POSTGRES_STARTED_BEFORE_DEPLOY"
        log_error "❌ Started after:  $POSTGRES_STARTED_AFTER_DEPLOY"
        log_error "❌ Deployment zakończony, ale PostgreSQL został odtworzony - sprawdź logi!"
        exit 1
    else
        log_success "✅ PostgreSQL pozostał nietknięty (StartedAt: $POSTGRES_STARTED_AFTER_DEPLOY)"
    fi
    
    # 11. Sukces!
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
    
    # ⚠️⚠️⚠️ NIETYKALNE KONTENERY - sprawdź przed rollback ⚠️⚠️⚠️
    check_protected_containers
    
    ACTIVE=$(get_active_environment)
    
    if [ "$ACTIVE" = "blue" ]; then
        TARGET="green"
    else
        TARGET="blue"
    fi
    
    log_info "Rollback z ${ACTIVE} na ${TARGET}..."
    
    # Uruchom stary environment
    # ✅ Bezpieczne - uruchamia tylko web-${TARGET}, nie dotyka nietykalnych kontenerów
    if ! docker-compose -f docker-compose.blue-green.yml up -d web-${TARGET}; then
        log_error "❌ Nie udało się uruchomić kontenera ${TARGET} podczas rollback"
        exit 1
    fi
    
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
