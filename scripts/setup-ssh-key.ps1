# Skrypt do dodania klucza SSH do .env.dev (jako base64)
# Uzycie: .\scripts\setup-ssh-key.ps1

$envFile = ".env.dev"
$sshKeyPath = "$env:USERPROFILE\.ssh\id_ed25519"

if (-not (Test-Path $sshKeyPath)) {
    Write-Host "Brak klucza SSH w $sshKeyPath" -ForegroundColor Red
    Write-Host "Wygeneruj klucz: ssh-keygen -t ed25519 -C 'twoj_email@example.com'" -ForegroundColor Yellow
    exit 1
}

Write-Host "Czytanie i kodowanie klucza SSH..." -ForegroundColor Green

# Przeczytaj klucz i zakoduj w base64
$sshKeyBytes = [System.IO.File]::ReadAllBytes($sshKeyPath)
$sshKeyBase64 = [System.Convert]::ToBase64String($sshKeyBytes)

# Czytaj istniejacy plik .env.dev
$envContent = @()
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile
}

# Usun stare wpisy SSH_* jesli istnieja
$envContent = $envContent | Where-Object { 
    $_ -notmatch "^SSH_KEY=" -and 
    $_ -notmatch "^SSH_HOST=" -and 
    $_ -notmatch "^SSH_USER=" -and 
    $_ -notmatch "^SSH_PORT=" -and
    $_ -notmatch "^# SSH"
}

# Dodaj nowe wpisy SSH
$newLines = @()
$newLines += "# SSH Configuration"
$newLines += "SSH_HOST=212.127.93.27"
$newLines += "SSH_USER=pawel"
$newLines += "SSH_PORT=22"
$newLines += "# SSH Key (zakodowany w base64)"
$newLines += "SSH_KEY=$sshKeyBase64"

# Dodaj nowe linie do zawartosci
$envContent += ""
$envContent += $newLines

# Zapisz z powrotem
$envContent | Set-Content $envFile -Encoding UTF8

Write-Host ""
Write-Host "[OK] Klucz SSH zostal dodany do $envFile (zakodowany w base64)" -ForegroundColor Green
Write-Host ""
Write-Host "Nastepne kroki:"
Write-Host "1. Sprawdz czy dane sa poprawne w $envFile"
Write-Host "2. Uruchom: docker-compose -f docker-compose.dev.yml up -d postgres-ssh-tunnel"
Write-Host "3. Sprawdz logi: docker-compose -f docker-compose.dev.yml logs -f postgres-ssh-tunnel"
