#!/bin/bash
# Automatyczny deployment blue-green z przełączaniem

set -e

APP_DIR="/home/pawel/apps/nc"
COMPOSE_FILE="$APP_DIR/docker-compose.blue-green.yml"
SWITCH_SCRIPT="$APP_DIR/switch-blue-green.sh"

# Określ aktualnie aktywny kolor
CURRENT_COLOR=$(docker exec nc-nginx-router cat /etc/nginx/state/active_backend.conf 2>/dev/null | grep -o "web-[a-z]*" | head -1 | sed 's/web-//' || echo "green")

# Określ kolor do deploymencie (przełącz na przeciwny)
if [ "$CURRENT_COLOR" = "green" ]; then
    DEPLOY_COLOR="blue"
else
    DEPLOY_COLOR="green"
fi

echo "🚀 Rozpoczynam deployment blue-green..."
echo "📊 Aktualnie aktywny: $CURRENT_COLOR"
echo "🔄 Deployuję na: $DEPLOY_COLOR"

cd "$APP_DIR"

# 1. Zbuduj nowy obraz
echo "🔨 Budowanie obrazu dla $DEPLOY_COLOR..."
docker compose -f "$COMPOSE_FILE" build web-$DEPLOY_COLOR

# 2. Zatrzymaj stary kontener (jeśli działa)
echo "⏸️  Zatrzymywanie starego $DEPLOY_COLOR (jeśli działa)..."
docker compose -f "$COMPOSE_FILE" stop web-$DEPLOY_COLOR || true

# 3. Uruchom nowy kontener
echo "▶️  Uruchamianie nowego $DEPLOY_COLOR..."
docker compose -f "$COMPOSE_FILE" up -d web-$DEPLOY_COLOR

# 4. Czekaj aż healthcheck przejdzie
echo "⏳ Czekam aż $DEPLOY_COLOR będzie gotowy..."
MAX_WAIT=120
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    HEALTH=$(docker inspect nc-web-$DEPLOY_COLOR --format '{{.State.Health.Status}}' 2>/dev/null || echo "starting")
    if [ "$HEALTH" = "healthy" ]; then
        echo "✅ $DEPLOY_COLOR jest healthy!"
        break
    fi
    echo "   Status: $HEALTH (czekam...)"
    sleep 5
    WAITED=$((WAITED + 5))
done

if [ "$HEALTH" != "healthy" ]; then
    echo "❌ Błąd: $DEPLOY_COLOR nie przeszedł healthcheck w czasie $MAX_WAIT sekund"
    echo "📋 Logi:"
    docker logs nc-web-$DEPLOY_COLOR --tail 50
    exit 1
fi

# 5. Przełącz ruch na nowy deployment
echo "🔄 Przełączanie ruchu na $DEPLOY_COLOR..."
bash "$SWITCH_SCRIPT" "$DEPLOY_COLOR"

# 6. Sprawdź czy przełączenie się powiodło
sleep 3
STATUS=$(docker exec nc-nginx-router cat /etc/nginx/state/active_backend.conf 2>/dev/null | grep -o "web-[a-z]*" | head -1 | sed 's/web-//' || echo "unknown")
echo "📊 Status po przełączeniu: $STATUS"

if [ "$STATUS" = "$DEPLOY_COLOR" ]; then
    echo "✅ Deployment zakończony pomyślnie! Aktywny: $DEPLOY_COLOR"
    
    # Opcjonalnie: zatrzymaj stary kontener po 5 minutach (rollback window)
    echo "⏰ Stary $CURRENT_COLOR zostanie zatrzymany za 5 minut (możesz anulować rollback)"
    (
        sleep 300
        echo "🛑 Zatrzymywanie starego $CURRENT_COLOR..."
        docker compose -f "$COMPOSE_FILE" stop web-$CURRENT_COLOR || true
    ) &
else
    echo "⚠️  Ostrzeżenie: Status nie zgadza się z oczekiwanym ($DEPLOY_COLOR vs $STATUS)"
fi

echo "✅ Deployment completed!"
