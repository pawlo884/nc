#!/bin/bash

echo "🚀 DEPLOY PRODUKCYJNY - PROSTY SPOSÓB"
echo "===================================="

# Sprawdź czy jesteś w odpowiednim katalogu
if [ ! -f "manage.py" ]; then
    echo "❌ Błąd: Nie jesteś w katalogu projektu!"
    exit 1
fi

echo "✅ Katalog projektu OK"

# Użyj Dockerfile.prod zamiast Dockerfile
echo "🔧 Używam Dockerfile.prod (bez plików dev)..."

# Zatrzymaj istniejące kontenery
echo "🛑 Zatrzymywanie istniejących kontenerów..."
docker-compose down

# Wyczyść cache
echo "🧹 Czyszczenie cache..."
docker system prune -f > /dev/null 2>&1

# Zbuduj z Dockerfile.prod
echo "🔨 Budowanie z Dockerfile.prod..."
docker build -f Dockerfile.prod -t nc-project:latest .

# Sprawdź czy build się powiódł
if [ $? -eq 0 ]; then
    echo "✅ Build zakończony pomyślnie!"
    
    # Uruchom z docker-compose
    echo "🚀 Uruchamianie aplikacji..."
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
    echo "  docker-compose logs -f celery # Logi Celery"
    echo "  docker-compose down           # Zatrzymaj wszystko"
    echo "  docker-compose restart web    # Restart aplikacji"
else
    echo "❌ Build nie powiódł się!"
    exit 1
fi
