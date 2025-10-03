Write-Host "🚀 Testowanie konfiguracji Nginx w development..." -ForegroundColor Green

Write-Host "📦 Budowanie i uruchamianie kontenerów..." -ForegroundColor Yellow
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d

Write-Host "⏳ Oczekiwanie na uruchomienie serwisów..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "🔍 Sprawdzanie statusu kontenerów..." -ForegroundColor Cyan
docker-compose -f docker-compose.dev.yml ps

Write-Host "🌐 Testowanie aplikacji na http://localhost:8000" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000" -Method Head -TimeoutSec 10
    Write-Host "✅ Aplikacja odpowiada: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "❌ Aplikacja nie odpowiada: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "📁 Testowanie plików statycznych na http://localhost:8000/static/" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/static/" -Method Head -TimeoutSec 10
    Write-Host "✅ Pliki statyczne odpowiadają: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "❌ Pliki statyczne nie odpowiadają: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "📊 Testowanie API na http://localhost:8000/api/" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/" -Method Head -TimeoutSec 10
    Write-Host "✅ API odpowiada: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "❌ API nie odpowiada: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "🌸 Testowanie Flower na http://localhost:5555" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5555" -Method Head -TimeoutSec 10
    Write-Host "✅ Flower odpowiada: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "❌ Flower nie odpowiada: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "✅ Test zakończony!" -ForegroundColor Green
Write-Host "📝 Sprawdź logi: docker-compose -f docker-compose.dev.yml logs" -ForegroundColor Yellow
