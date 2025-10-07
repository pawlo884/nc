#!/bin/bash
# Zero-Downtime Deployment z Docker Registry (Docker Hub)
# Dla użycia z GitHub Actions

set -e

echo "🚀 ZERO-DOWNTIME DEPLOYMENT (Docker Hub)"
echo "========================================="
echo ""

# Konfiguracja
COMPOSE_FILE="docker-compose.prod.yml"
NEW_TAG="django-app:new-$(date +%Y%m%d-%H%M%S)"
OLD_TAG="django-app:current"
REGISTRY_IMAGE="${DOCKERHUB_USERNAME}/django-app:latest"

echo "📋 Konfiguracja:"
echo "   Compose file: $COMPOSE_FILE"
echo "   Registry: $REGISTRY_IMAGE"
echo "   Nowy tag: $NEW_TAG"
echo "   Stary tag: $OLD_TAG"
echo ""

# Krok 1: Pobierz NOWY obraz (stary nadal działa!)
echo "📥 Pobieram NOWY obraz z Docker Hub (stary nadal działa)..."
docker pull $REGISTRY_IMAGE

if [ $? -ne 0 ]; then
    echo "❌ Błąd podczas pobierania obrazu!"
    exit 1
fi

echo "✅ Nowy obraz pobrany"
echo ""

# Krok 2: Backup starego obrazu
echo "💾 Tworzę backup starego obrazu..."
EXISTING_IMAGE=$(docker images -q $OLD_TAG 2>/dev/null)
if [ -n "$EXISTING_IMAGE" ]; then
    BACKUP_TAG="django-app:backup-$(date +%Y%m%d-%H%M%S)"
    docker tag $OLD_TAG $BACKUP_TAG
    echo "✅ Backup utworzony: $BACKUP_TAG"
else
    echo "⚠️  Brak starego obrazu (pierwszy deploy)"
fi
echo ""

# Krok 3: Oznacz nowy obraz jako current
echo "🏷️  Oznaczam nowy obraz jako current..."
docker tag $REGISTRY_IMAGE $NEW_TAG
docker tag $NEW_TAG $OLD_TAG
echo "✅ Nowy obraz oznaczony"
echo ""

# Krok 4: Szybkie przełączenie (2-5s downtime)
echo "🔄 Przełączam na nowy obraz..."
echo "   Downtime: ~2-5 sekund"

SWITCH_START=$(date +%s)

# Stop kontenerów
docker-compose -f $COMPOSE_FILE stop

# Remove kontenerów (volumes zostają!)
docker-compose -f $COMPOSE_FILE rm -f

# Start z nowym obrazem
docker-compose -f $COMPOSE_FILE up -d

SWITCH_END=$(date +%s)
SWITCH_TIME=$((SWITCH_END - SWITCH_START))

echo "✅ Przełączono w ${SWITCH_TIME}s"
echo ""

# Krok 5: Health check
echo "🏥 Health check..."
sleep 5

MAX_RETRIES=12
RETRY_COUNT=0
HEALTH_OK=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "   Próba $RETRY_COUNT/$MAX_RETRIES..."
    
    UNHEALTHY=$(docker-compose -f $COMPOSE_FILE ps | grep -E "Exit|unhealthy" || true)
    
    if [ -z "$UNHEALTHY" ]; then
        HEALTH_OK=true
        break
    fi
    
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        sleep 5
    fi
done

if [ "$HEALTH_OK" != "true" ]; then
    echo "❌ Health check failed!"
    echo ""
    echo "🔙 ROLLBACK..."
    
    if [ -n "$BACKUP_TAG" ]; then
        docker tag $BACKUP_TAG $OLD_TAG
        docker-compose -f $COMPOSE_FILE up -d --force-recreate
        echo "✅ Rollback zakończony"
    fi
    
    exit 1
fi

echo "✅ Health check passed!"
echo ""

# Krok 6: Status
echo "📊 Status kontenerów:"
docker-compose -f $COMPOSE_FILE ps
echo ""

# Krok 7: Cleanup starych obrazów (zostaw 3)
echo "🧹 Cleanup starych obrazów..."
docker images "django-app" --format "{{.ID}}" | tail -n +4 | xargs -r docker rmi -f 2>/dev/null || true
echo "✅ Cleanup zakończony"
echo ""

# Podsumowanie
echo "🎉 DEPLOYMENT ZAKOŃCZONY!"
echo "=========================="
echo ""
echo "📈 Statystyki:"
echo "   Downtime: ~${SWITCH_TIME}s"
echo "   Backup: $BACKUP_TAG"
echo ""
echo "💡 W razie problemów rollback:"
echo "   docker tag $BACKUP_TAG $OLD_TAG"
echo "   docker-compose -f $COMPOSE_FILE up -d --force-recreate"
echo ""

