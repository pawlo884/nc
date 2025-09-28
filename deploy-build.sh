#!/bin/bash

# Skrypt do budowania i deploy bez cache
echo "🚀 Budowanie obrazu dla deploy..."

# Wyczyść cache
echo "🧹 Czyszczenie cache..."
docker builder prune -f

# Zbuduj obraz bez cache
echo "🔨 Budowanie obrazu bez cache..."
docker build --no-cache --pull -t nc-project:latest .

# Sprawdź czy build się powiódł
if [ $? -eq 0 ]; then
    echo "✅ Build zakończony pomyślnie!"
    
    # Opcjonalnie: wypchnij do Docker Hub
    if [ ! -z "$DOCKERHUB_USERNAME" ]; then
        echo "📤 Wypychanie do Docker Hub..."
        docker tag nc-project:latest ${DOCKERHUB_USERNAME}/django-app:latest
        docker push ${DOCKERHUB_USERNAME}/django-app:latest
    fi
    
    echo "🎉 Gotowe do deploy!"
else
    echo "❌ Build nie powiódł się!"
    exit 1
fi
