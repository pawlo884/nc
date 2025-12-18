#!/bin/bash
# Szybki build z cache'owaniem BuildKit
# Ten skrypt używa BuildKit do cache'owania warstw i pakietów

echo "🚀 Szybki build z BuildKit cache..."

# Włącz BuildKit
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Build z cache'owaniem
echo "📦 Buduję obraz z cache'owaniem pakietów..."
docker-compose -f docker-compose.dev.yml build --parallel

echo "✅ Build zakończony!"
echo ""
echo "💡 Następne buildy będą znacznie szybsze dzięki cache'owaniu!"
echo "   - Pakiety systemowe (apt) są cache'owane"
echo "   - Pakiety Python (pip) są cache'owane"
echo "   - Rebuild będzie szybki jeśli zmienisz tylko kod aplikacji"
echo ""
echo "🔄 Aby uruchomić kontenery użyj:"
echo "   docker-compose -f docker-compose.dev.yml up -d"

