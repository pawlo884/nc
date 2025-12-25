#!/bin/bash

# Skrypt do budowania bez cache dla deploy
echo "🚀 Budowanie obrazu Docker bez cache..."

# Wyczyść cache Docker
echo "🧹 Czyszczenie cache Docker..."
docker builder prune -f

# Zbuduj obraz bez cache
echo "🔨 Budowanie obrazu bez cache..."
docker build --no-cache --pull -t nc-project:latest .

# Sprawdź czy build się powiódł
if [ $? -eq 0 ]; then
    echo "✅ Build zakończony pomyślnie!"
    echo "📊 Rozmiar obrazu:"
    docker images nc-project:latest
else
    echo "❌ Build nie powiódł się!"
    exit 1
fi

# Opcjonalnie: uruchom testy
echo "🧪 Uruchamianie testów..."
docker run --rm nc-project:latest python manage.py check --deploy

echo "🎉 Gotowe!"
