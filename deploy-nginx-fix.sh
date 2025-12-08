#!/bin/bash

# Skrypt do wdrożenia poprawki nginx dla portu 8001
# Użycie: ./deploy-nginx-fix.sh

set -e

echo "🔧 Wdrażanie poprawki nginx dla portu 8001..."

# Kolory dla output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funkcja logowania
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Sprawdź czy jesteśmy w katalogu projektu
if [ ! -f "docker-compose.prod.yml" ]; then
    log_error "Nie znaleziono docker-compose.prod.yml. Uruchom skrypt z katalogu projektu."
    exit 1
fi

# 2. Sprawdź czy pliki konfiguracyjne istnieją
if [ ! -f "nginx.conf" ]; then
    log_error "Nie znaleziono nginx.conf"
    exit 1
fi

log_info "✅ Pliki konfiguracyjne znalezione"

# 3. Walidacja konfiguracji nginx (jeśli możliwe)
log_info "🔍 Walidacja konfiguracji nginx..."
if docker run --rm -v "$(pwd)/nginx.conf:/etc/nginx/conf.d/default.conf:ro" nginx:alpine nginx -t 2>/dev/null; then
    log_info "✅ Konfiguracja nginx jest poprawna"
else
    log_warn "⚠️  Nie można zwalidować konfiguracji nginx (może nie być Docker), kontynuuję..."
fi

# 4. Backup obecnej konfiguracji
log_info "💾 Tworzenie backupu konfiguracji..."
BACKUP_DIR="backups/nginx-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

if docker-compose -f docker-compose.prod.yml exec -T nginx cat /etc/nginx/conf.d/default.conf > "$BACKUP_DIR/nginx.conf.backup" 2>/dev/null; then
    log_info "✅ Backup utworzony w $BACKUP_DIR"
else
    log_warn "⚠️  Nie można utworzyć backupu z kontenera (może być wyłączony), kopiuję lokalny..."
    cp nginx.conf "$BACKUP_DIR/nginx.conf.backup" 2>/dev/null || true
fi

# 5. Sprawdź status kontenerów
log_info "📊 Sprawdzanie statusu kontenerów..."
docker-compose -f docker-compose.prod.yml ps

# 6. Sprawdź czy web działa
log_info "🔍 Sprawdzanie czy kontener web działa..."
if docker-compose -f docker-compose.prod.yml ps | grep -q "web.*Up"; then
    log_info "✅ Kontener web działa"
else
    log_error "❌ Kontener web nie działa! Napraw problem przed kontynuacją."
    exit 1
fi

# 7. Test połączenia web:8000 z poziomu nginx
log_info "🔍 Test połączenia do web:8000..."
if docker-compose -f docker-compose.prod.yml exec -T nginx wget -q -O- --timeout=5 http://web:8000/ 2>/dev/null | head -1 > /dev/null; then
    log_info "✅ Połączenie do web:8000 działa"
else
    log_warn "⚠️  Nie można przetestować połączenia do web:8000 (może być normalne jeśli nginx nie działa)"
fi

# 8. Zatrzymaj nginx (jeśli działa)
log_info "⏸️  Zatrzymywanie nginx..."
docker-compose -f docker-compose.prod.yml stop nginx || true

# 9. Uruchom nginx z nową konfiguracją
log_info "🚀 Uruchamianie nginx z nową konfiguracją..."
docker-compose -f docker-compose.prod.yml up -d nginx

# 10. Sprawdź czy nginx się uruchomił
sleep 3
if docker-compose -f docker-compose.prod.yml ps | grep -q "nginx.*Up"; then
    log_info "✅ Nginx uruchomiony"
else
    log_error "❌ Nginx nie uruchomił się poprawnie!"
    log_info "Sprawdź logi: docker-compose -f docker-compose.prod.yml logs nginx"
    exit 1
fi

# 11. Sprawdź logi nginx
log_info "📋 Sprawdzanie logów nginx (ostatnie 10 linii)..."
docker-compose -f docker-compose.prod.yml logs --tail=10 nginx

# 12. Test health check
log_info "🏥 Test health check..."
sleep 2
if curl -s -f http://localhost:80/nginx-health > /dev/null; then
    log_info "✅ Health check na porcie 80 działa"
else
    log_warn "⚠️  Health check na porcie 80 nie odpowiada"
fi

if curl -s -f http://localhost:8001/nginx-health > /dev/null; then
    log_info "✅ Health check na porcie 8001 działa"
else
    log_warn "⚠️  Health check na porcie 8001 nie odpowiada (może być normalne jeśli port nie jest dostępny lokalnie)"
fi

# 13. Test konfiguracji nginx w kontenerze
log_info "🔍 Test konfiguracji nginx w kontenerze..."
if docker-compose -f docker-compose.prod.yml exec -T nginx nginx -t; then
    log_info "✅ Konfiguracja nginx w kontenerze jest poprawna"
else
    log_error "❌ Konfiguracja nginx w kontenerze jest niepoprawna!"
    log_info "Przywracanie backupu..."
    cp "$BACKUP_DIR/nginx.conf.backup" nginx.conf
    docker-compose -f docker-compose.prod.yml restart nginx
    exit 1
fi

log_info ""
log_info "✅ Wdrożenie zakończone pomyślnie!"
log_info ""
log_info "📝 Następne kroki:"
log_info "   1. Przetestuj dostępność: curl http://212.127.93.27:8001/nginx-health"
log_info "   2. Sprawdź logi: docker-compose -f docker-compose.prod.yml logs -f nginx"
log_info "   3. Backup znajduje się w: $BACKUP_DIR"
log_info ""
log_info "🔄 W razie problemów, przywróć backup:"
log_info "   cp $BACKUP_DIR/nginx.conf.backup nginx.conf"
log_info "   docker-compose -f docker-compose.prod.yml restart nginx"

