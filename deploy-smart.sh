#!/bin/bash

echo "🚀 SMART DEPLOY - INTELIGENTNY DEPLOY"
echo "====================================="

# Sprawdź czy jesteś w odpowiednim katalogu
if [ ! -f "manage.py" ]; then
    echo "❌ Błąd: Nie jesteś w katalogu projektu!"
    echo "Uruchom: cd /ścieżka/do/nc_project"
    exit 1
fi

echo "✅ Katalog projektu OK"

# Funkcja sprawdzająca czy potrzebny jest rebuild
check_if_rebuild_needed() {
    local needs_rebuild=false
    
    # Sprawdź czy requirements.txt się zmienił
    if [ -f "requirements.txt" ]; then
        if [ ! -f ".requirements_hash" ] || [ "$(md5sum requirements.txt | cut -d' ' -f1)" != "$(cat .requirements_hash 2>/dev/null)" ]; then
            echo "📦 requirements.txt się zmienił - wymagany rebuild"
            needs_rebuild=true
        fi
    fi
    
    # Sprawdź czy Dockerfile się zmienił
    if [ -f "Dockerfile.prod" ]; then
        if [ ! -f ".dockerfile_hash" ] || [ "$(md5sum Dockerfile.prod | cut -d' ' -f1)" != "$(cat .dockerfile_hash 2>/dev/null)" ]; then
            echo "🐳 Dockerfile.prod się zmienił - wymagany rebuild"
            needs_rebuild=true
        fi
    fi
    
    # Sprawdź czy docker-compose.yml się zmienił
    if [ -f "docker-compose.yml" ]; then
        if [ ! -f ".dockercompose_hash" ] || [ "$(md5sum docker-compose.yml | cut -d' ' -f1)" != "$(cat .dockercompose_hash 2>/dev/null)" ]; then
            echo "🔧 docker-compose.yml się zmienił - wymagany rebuild"
            needs_rebuild=true
        fi
    fi
    
    # Sprawdź czy obraz istnieje
    if ! docker images | grep -q "app-web.*latest"; then
        echo "🆕 Brak obrazu aplikacji - wymagany rebuild"
        needs_rebuild=true
    fi
    
    echo $needs_rebuild
}

# Sprawdź czy potrzebny jest rebuild
if [ "$(check_if_rebuild_needed)" = "true" ]; then
    echo ""
    echo "🔨 WYMAGANY REBUILD - budowanie obrazów..."
    
    # Ustaw datę budowania
    export BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    echo "📅 Data budowania: $BUILD_DATE"
    
    # Zatrzymaj kontenery
    echo "🛑 Zatrzymywanie kontenerów..."
    docker-compose down
    
    # Zbuduj obrazy
    echo "🔨 Budowanie obrazów..."
    docker-compose build --no-cache
    
    # Zapisz hashe plików
    if [ -f "requirements.txt" ]; then
        md5sum requirements.txt | cut -d' ' -f1 > .requirements_hash
    fi
    if [ -f "Dockerfile.prod" ]; then
        md5sum Dockerfile.prod | cut -d' ' -f1 > .dockerfile_hash
    fi
    if [ -f "docker-compose.yml" ]; then
        md5sum docker-compose.yml | cut -d' ' -f1 > .dockercompose_hash
    fi
    
    echo "✅ Rebuild zakończony"
else
    echo ""
    echo "⚡ REBUILD NIE POTRZEBNY - używam istniejących obrazów"
    echo "💡 Rebuild jest potrzebny tylko gdy zmieni się:"
    echo "   - requirements.txt (nowe pakiety Python)"
    echo "   - Dockerfile.prod (zmiany w obrazie)"
    echo "   - docker-compose.yml (zmiany w konfiguracji)"
    echo ""
    echo "🔄 Restart kontenerów..."
    docker-compose down
fi

# Uruchom aplikację
echo "🚀 Uruchamianie aplikacji..."
docker-compose up -d

# Sprawdź status
echo "📊 Sprawdzanie statusu..."
sleep 10
docker-compose ps

# Sprawdź logi web
echo "📋 Sprawdzanie logów web..."
docker-compose logs --tail=10 web

echo ""
echo "🎉 DEPLOY ZAKOŃCZONY!"
echo "📱 Aplikacja dostępna na: http://localhost:8000"
echo "🌺 Flower (Celery monitoring): http://localhost:5555"
echo ""
echo "💡 Dla następnych deployów:"
echo "  ./deploy-smart.sh  # Inteligentny deploy (zalecany)"
echo "  ./deploy-force-rebuild.sh  # Wymuszony rebuild (gdy potrzebny)"
echo ""
echo "📋 Przydatne komendy:"
echo "  docker-compose logs -f web     # Logi aplikacji"
echo "  docker-compose logs -f celery  # Logi Celery"
echo "  docker-compose down            # Zatrzymaj wszystko"
echo "  docker-compose restart web     # Restart aplikacji"

