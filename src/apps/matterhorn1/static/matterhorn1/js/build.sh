#!/bin/bash

# Skrypt do budowania React komponentów dla Matterhorn1

echo "Instalowanie zależności..."
npm install

echo "Budowanie React komponentów..."
npm run build

echo "Kopiowanie plików do katalogu dist..."
mkdir -p dist
cp -r ../dist/* dist/

echo "Budowanie zakończone!"
echo "Pliki znajdują się w: matterhorn1/static/matterhorn1/js/dist/"
