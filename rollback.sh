#!/bin/bash
# Rollback do poprzedniej wersji obrazu

set -e

ENVIRONMENT=${1:-dev}

echo "🔙 ROLLBACK DO POPRZEDNIEJ WERSJI"
echo "====================================="
echo ""

COMPOSE_FILE=$([ "$ENVIRONMENT" = "dev" ] && echo "docker-compose.dev.yml" || echo "docker-compose.yml")

# Znajdź ostatni backup
echo "🔍 Szukam ostatniego backupu..."
BACKUP_IMAGES=$(docker images "nc-app" --format "{{.Repository}}:{{.Tag}}" | grep "backup-" | sort -r)

if [ -z "$BACKUP_IMAGES" ]; then
    echo "❌ Nie znaleziono żadnych backupów!"
    echo "   Brak obrazów do przywrócenia"
    exit 1
fi

echo "📦 Dostępne backupy:"
i=1
while IFS= read -r backup; do
    echo "   $i) $backup"
    i=$((i + 1))
done <<< "$BACKUP_IMAGES"
echo ""

read -p "Wybierz numer backupu (Enter = najnowszy): " choice
if [ -z "$choice" ]; then
    choice=1
fi

SELECTED_BACKUP=$(echo "$BACKUP_IMAGES" | sed -n "${choice}p")

if [ -z "$SELECTED_BACKUP" ]; then
    echo "❌ Nieprawidłowy wybór!"
    exit 1
fi

echo ""
echo "🔄 Przywracam backup: $SELECTED_BACKUP"

# Oznacz backup jako current
docker tag $SELECTED_BACKUP "nc-app:current"

# Restart kontenerów z nowym/starym obrazem
echo "🔄 Restartuję kontenery..."
docker-compose -f $COMPOSE_FILE up -d --force-recreate

echo ""
echo "✅ ROLLBACK ZAKOŃCZONY!"
echo ""
echo "📊 Status kontenerów:"
docker-compose -f $COMPOSE_FILE ps
echo ""

