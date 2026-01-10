#!/bin/bash
# Skrypt do automatycznego przełączania między blue/green deployment

set -e

COLOR=$1
NGINX_ROUTER_CONTAINER="nc-nginx-router"
STATE_DIR="/mnt/data2tb/docker/volumes/nc_nginx_state"

if [ -z "$COLOR" ]; then
    echo "Użycie: $0 [blue|green]"
    echo "Przełącza aktywny backend na blue lub green"
    exit 1
fi

if [ "$COLOR" != "blue" ] && [ "$COLOR" != "green" ]; then
    echo "Błąd: Kolor musi być 'blue' lub 'green'"
    exit 1
fi

echo "🔄 Przełączanie na $COLOR..."

# Utwórz katalog jeśli nie istnieje
mkdir -p "$STATE_DIR"

# Utwórz plik konfiguracyjny z aktywnym backendem
cat > "$STATE_DIR/active_backend.conf" <<EOF
# Automatycznie wygenerowane przez switch-blue-green.sh
# Nie edytuj ręcznie - użyj skryptu switch-blue-green.sh

upstream backend_active {
    server web-${COLOR}:8000 max_fails=3 fail_timeout=30s;
}
EOF

# Przeładuj konfigurację nginx bez restartu (zero-downtime)
if docker exec "$NGINX_ROUTER_CONTAINER" nginx -t > /dev/null 2>&1; then
    echo "✅ Konfiguracja nginx poprawna, przeładowuję..."
    docker exec "$NGINX_ROUTER_CONTAINER" nginx -s reload
    echo "✅ Przełączono na $COLOR"
else
    echo "❌ Błąd w konfiguracji nginx, restartuję kontener..."
    docker restart "$NGINX_ROUTER_CONTAINER"
    echo "✅ Kontener zrestartowany z konfiguracją $COLOR"
fi

# Sprawdź status
echo ""
echo "📊 Status:"
ACTIVE_COLOR=$(docker exec "$NGINX_ROUTER_CONTAINER" cat /etc/nginx/state/active_backend.conf 2>/dev/null | grep -o "web-[a-z]*" | head -1 | sed 's/web-//' || echo "unknown")
echo "Aktywny backend: $ACTIVE_COLOR"
