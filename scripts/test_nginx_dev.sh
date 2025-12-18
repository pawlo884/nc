#!/bin/bash

echo "🚀 Testowanie konfiguracji Nginx w development..."

echo "📦 Budowanie i uruchamianie kontenerów..."
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d

echo "⏳ Oczekiwanie na uruchomienie serwisów..."
sleep 30

echo "🔍 Sprawdzanie statusu kontenerów..."
docker-compose -f docker-compose.dev.yml ps

echo "🌐 Testowanie aplikacji na http://localhost:8000"
curl -I http://localhost:8000

echo "📁 Testowanie plików statycznych na http://localhost:8000/static/"
curl -I http://localhost:8000/static/

echo "📊 Testowanie API na http://localhost:8000/api/"
curl -I http://localhost:8000/api/

echo "🌸 Testowanie Flower na http://localhost:5555"
curl -I http://localhost:5555

echo "✅ Test zakończony!"
echo "📝 Sprawdź logi: docker-compose -f docker-compose.dev.yml logs"
