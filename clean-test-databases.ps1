# Skrypt do czyszczenia testowych baz danych PostgreSQL
# PowerShell script

Write-Host "🧹 Czyszczenie testowych baz danych..." -ForegroundColor Blue

# Pobierz zmienne środowiskowe z .env.dev
$envFile = ".env.dev"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

$dbHost = $env:DEFAULT_DB_HOST
$dbPort = $env:DEFAULT_DB_PORT
$dbUser = $env:DEFAULT_DB_USER
$dbPassword = $env:DEFAULT_DB_PASSWORD

if (-not $dbHost) {
    Write-Host "❌ Nie znaleziono zmiennych środowiskowych z .env.dev" -ForegroundColor Red
    Write-Host "Upewnij się, że plik .env.dev istnieje i zawiera konfigurację baz danych" -ForegroundColor Yellow
    exit 1
}

Write-Host "`nUsuwanie testowych baz danych..." -ForegroundColor Yellow

# Lista testowych baz do usunięcia
$testDatabases = @(
    "test_zzz_default",
    "test_zzz_MPD",
    "test_zzz_matterhorn1",
    "test_zzz_web_agent"
)

# Ustaw zmienną środowiskową PGPASSWORD dla psql
$env:PGPASSWORD = $dbPassword

foreach ($dbName in $testDatabases) {
    Write-Host "  Usuwanie $dbName..." -ForegroundColor Cyan
    
    # Sprawdź czy baza istnieje i usuń ją
    $checkQuery = "SELECT 1 FROM pg_database WHERE datname = '$dbName';"
    $exists = psql -h $dbHost -p $dbPort -U $dbUser -d postgres -t -c $checkQuery 2>$null
    
    if ($exists) {
        # Zakończ wszystkie połączenia do bazy
        psql -h $dbHost -p $dbPort -U $dbUser -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$dbName' AND pid <> pg_backend_pid();" 2>$null | Out-Null
        
        # Usuń bazę
        psql -h $dbHost -p $dbPort -U $dbUser -d postgres -c "DROP DATABASE IF EXISTS $dbName;" 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    ✅ $dbName usunięta" -ForegroundColor Green
        } else {
            Write-Host "    ⚠️  Nie udało się usunąć $dbName (może nie istnieć)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "    ℹ️  $dbName nie istnieje" -ForegroundColor Gray
    }
}

Write-Host "`n✅ Czyszczenie zakończone!" -ForegroundColor Green
Write-Host "`nMożesz teraz uruchomić testy:" -ForegroundColor Cyan
Write-Host "  python manage.py test --settings=nc.settings.dev" -ForegroundColor White

