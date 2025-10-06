#!/bin/bash

echo "🚀 DEPLOY NC PROJECT"
echo "==================="
echo ""
echo "Wybierz typ deploy:"
echo "1) Smart deploy (zalecany) - przebudowuje tylko gdy potrzeba"
echo "2) Force rebuild - zawsze przebudowuje wszystko"
echo "3) Exit"
echo ""
read -p "Wybierz opcję (1-3): " choice

case $choice in
    1)
        echo ""
        echo "🔄 Uruchamianie smart deploy..."
        ./deploy-smart.sh
        ;;
    2)
        echo ""
        echo "🔨 Uruchamianie force rebuild..."
        ./deploy-force-rebuild.sh
        ;;
    3)
        echo "❌ Anulowano deploy"
        exit 0
        ;;
    *)
        echo "❌ Nieprawidłowa opcja. Uruchamiam smart deploy..."
        ./deploy-smart.sh
        ;;
esac