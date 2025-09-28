#!/bin/bash

echo "🚀 DEPLOY NC PROJECT - PROSTY SPOSÓB"
echo "=================================="

# Sprawdź czy jesteś w odpowiednim katalogu
if [ ! -f "manage.py" ]; then
    echo "❌ Błąd: Nie jesteś w katalogu projektu!"
    echo "Uruchom: cd /ścieżka/do/nc_project"
    exit 1
fi

echo "✅ Katalog projektu OK"

# Wyczyść cache Docker (opcjonalnie)
echo "🧹 Czyszczenie cache Docker..."
docker system prune -f > /dev/null 2>&1

# Zbuduj i uruchom
echo "🔨 Budowanie i uruchamianie aplikacji..."
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Sprawdź status
echo "📊 Sprawdzanie statusu..."
sleep 10
docker-compose ps

echo ""
echo "🎉 GOTOWE!"
echo "📱 Aplikacja dostępna na: http://localhost:8000"
echo "🌺 Flower (Celery monitoring): http://localhost:5555"
echo ""
echo "📋 Przydatne komendy:"
echo "  docker-compose logs -f web     # Logi aplikacji"
echo "  docker-compose logs -f celery  # Logi Celery"
echo "  docker-compose down            # Zatrzymaj wszystko"
echo "  docker-compose restart web     # Restart aplikacji"
