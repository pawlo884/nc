# Tworzy Secret nc-env w namespace nc-test z pliku .env.test
# Uzycie: .\scripts\k8s-test\create-secret.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$EnvFile = Join-Path $RepoRoot ".env.test"

if (-not (Test-Path $EnvFile)) {
    throw "Brak pliku $EnvFile - skopiuj docs/env.test.sample.md i uzupelnij."
}

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    throw "Brak kubectl."
}

Write-Host "Tworzenie/aktualizacja secret nc-env w namespace nc-test..."
kubectl create namespace nc-test --dry-run=client -o yaml | kubectl apply -f -
kubectl delete secret nc-env -n nc-test --ignore-not-found
kubectl create secret generic nc-env --from-env-file=$EnvFile -n nc-test
Write-Host "Secret nc-env utworzony."
