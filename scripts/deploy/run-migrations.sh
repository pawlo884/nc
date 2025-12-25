#!/bin/bash

################################################################################
# Skrypt do ręcznego wykonywania migracji na produkcji
# 
# ⚠️ WAŻNE: Migracje powinny być wykonywane PRZED deploymentem
# Użyj tego skryptu gdy masz nowe migracje do zastosowania
################################################################################

set -e  # Exit on error

# Kolory do outputu
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Sprawdź czy jesteśmy w odpowiednim katalogu
if [ ! -f "docker-compose.blue-green.yml" ]; then
    log_error "❌ Nie znaleziono docker-compose.blue-green.yml"
    log_info "Uruchom skrypt z katalogu głównego projektu"
    exit 1
fi

# Określ aktywny environment
ACTIVE=$(docker ps --format '{{.Names}}' | grep -E 'nc-web-(blue|green)' | head -1 | sed 's/nc-web-//')

if [ -z "$ACTIVE" ]; then
    log_error "❌ Nie znaleziono aktywnego kontenera web (blue/green)"
    exit 1
fi

log_info "🔍 Aktywny environment: ${ACTIVE}"
log_warning "⚠️  Wykonuję migracje na kontenerze: nc-web-${ACTIVE}"

# Wykonaj migracje
log_info "🔄 Uruchamianie migracji..."

docker exec nc-web-${ACTIVE} python manage.py migrate --database=default --noinput
docker exec nc-web-${ACTIVE} python manage.py migrate admin_interface --database=default --noinput
docker exec nc-web-${ACTIVE} python manage.py migrate matterhorn1 --database=matterhorn1 --noinput
docker exec nc-web-${ACTIVE} python manage.py migrate MPD --database=MPD --noinput

log_success "✅ Migracje zakończone pomyślnie!"

