#!/bin/bash

# Tworzenie katalogów dla Celery
mkdir -p /var/lib/celery
chmod 777 /var/lib/celery

# Tworzenie katalogów dla logów
mkdir -p /app/logs/matterhorn
mkdir -p /app/logs
chmod 755 /app/logs/matterhorn
chmod 755 /app/logs

# Utwórz pliki logów jeśli nie istnieją
touch /app/logs/security.log
touch /app/logs/django.log
chmod 666 /app/logs/security.log
chmod 666 /app/logs/django.log

# Sprawdzenie i naprawa plików statycznych w produkcji
if [ "$DJANGO_SETTINGS_MODULE" = "nc.settings.prod" ]; then
    echo "🔧 Sprawdzanie plików statycznych w produkcji..."
    
    # Sprawdź czy pliki admin_interface istnieją
    if [ ! -d "/app/staticfiles/admin_interface" ]; then
        echo "⚠️  Brak plików admin_interface, naprawianie..."
        python manage.py collectstatic --clear --noinput
        echo "✅ Pliki statyczne naprawione"
    else
        echo "✅ Pliki statyczne admin_interface są dostępne"
    fi
    
    # Sprawdź uprawnienia plików statycznych
    chown -R celery:celery /app/staticfiles 2>/dev/null || true
    chmod -R 755 /app/staticfiles 2>/dev/null || true
fi

# Uruchomienie właściwej komendy
exec "$@" 