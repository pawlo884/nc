@echo off
echo Instalowanie zależności...
npm install

echo Budowanie React komponentów...
npm run build

echo Budowanie zakończone!
echo Pliki znajdują się w: matterhorn1/static/matterhorn1/js/dist/
pause
