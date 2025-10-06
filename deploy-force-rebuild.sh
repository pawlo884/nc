#!/bin/bash

echo "🚀 DEPLOY Z WYMUSZONYM REBUILD"
echo "=============================="

# Sprawdź czy jesteś w odpowiednim katalogu
if [ ! -f "manage.py" ]; then
    echo "❌ Błąd: Nie jesteś w katalogu projektu!"
    echo "Uruchom: cd /ścieżka/do/nc_project"
    exit 1
fi

echo "✅ Katalog projektu OK"

# Ustaw datę budowania
export BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
echo "📅 Data budowania: $BUILD_DATE"

# Zatrzymaj wszystkie kontenery
echo "🛑 Zatrzymywanie wszystkich kontenerów..."
docker-compose down

# Wyczyść cache i stare obrazy
echo "🧹 Czyszczenie cache Docker..."
docker system prune -f
docker image prune -f
docker builder prune -f

# Usuń stare obrazy aplikacji
echo "🗑️ Usuwanie starych obrazów aplikacji..."
docker images | grep -E "(app-|nc-project)" | awk '{print $3}' | xargs -r docker rmi -f

# Zbuduj wszystkie serwisy bez cache
echo "🔨 Budowanie wszystkich serwisów bez cache..."
docker-compose build --no-cache --pull

# Sprawdź czy build się powiódł
if [ $? -eq 0 ]; then
    echo "✅ Build zakończony pomyślnie!"
    
    # Uruchom aplikację
    echo "🚀 Uruchamianie aplikacji..."
    docker-compose up -d
    
    # Sprawdź status
    echo "📊 Sprawdzanie statusu..."
    sleep 15
    docker-compose ps
    
    # Sprawdź logi web
    echo "📋 Sprawdzanie logów web..."
    docker-compose logs --tail=20 web
    
    echo ""
    echo "🎉 DEPLOY ZAKOŃCZONY!"
    echo "📱 Aplikacja dostępna na: http://localhost:8000"
    echo "🌺 Flower (Celery monitoring): http://localhost:5555"
    echo ""
    echo "📋 Przydatne komendy:"
    echo "  docker-compose logs -f web     # Logi aplikacji"
    echo "  docker-compose logs -f celery  # Logi Celery"
    echo "  docker-compose down            # Zatrzymaj wszystko"
    echo "  docker-compose restart web     # Restart aplikacji"
    echo ""
    echo "🔍 Sprawdź czy drf-spectacular jest zainstalowany:"
    echo "  docker-compose exec web python -c \"import drf_spectacular; print('drf-spectacular OK')\""
else
    echo "❌ Build nie powiódł się!"
    exit 1
fi


