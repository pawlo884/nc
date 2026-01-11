# Szybki build z cache'owaniem BuildKit
# Ten skrypt używa BuildKit do cache'owania warstw i pakietów

Write-Host "🚀 Szybki build z BuildKit cache..." -ForegroundColor Green

# Włącz BuildKit
$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"

# Build z cache'owaniem
Write-Host "📦 Buduję obraz z cache'owaniem pakietów..." -ForegroundColor Cyan
docker-compose -f docker-compose/docker-compose.dev.yml build --parallel

Write-Host "✅ Build zakończony!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Następne buildy będą znacznie szybsze dzięki cache'owaniu!" -ForegroundColor Yellow
Write-Host "   - Pakiety systemowe (apt) są cache'owane"
Write-Host "   - Pakiety Python (pip) są cache'owane"
Write-Host "   - Rebuild będzie szybki jeśli zmienisz tylko kod aplikacji"
Write-Host ""
Write-Host "🔄 Aby uruchomić kontenery użyj:" -ForegroundColor Cyan
Write-Host "   docker-compose -f docker-compose/docker-compose.dev.yml up -d"

