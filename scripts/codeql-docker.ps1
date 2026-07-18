# Lokalny CodeQL w Dockerze — bez GitHub Actions / bez minut CI.
# Wymaga: Docker Desktop
#
#   .\scripts\codeql-docker.ps1
#   .\scripts\codeql-docker.ps1 -Langs python,javascript
#   .\scripts\codeql-docker.ps1 -Pull

param(
    [string]$Langs = "python",
    [switch]$Pull
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

New-Item -ItemType Directory -Force -Path (Join-Path $Root ".codeql") | Out-Null

$Compose = Join-Path $Root "docker-compose\docker-compose.codeql.yml"
$env:CODEQL_LANGS = $Langs

if ($Pull) {
    docker compose -f $Compose pull codeql
}

Write-Host "CodeQL langs=$Langs -> wyniki w .codeql\"
# NIE uzywaj --remove-orphans: ten sam katalog compose = ten sam project name co dev,
# i orphans kasuje kontenery web/redis/postgres.
docker compose -p nc-codeql -f $Compose run --rm codeql

if (Test-Path (Join-Path $Root ".codeql\python.sarif")) {
    Write-Host "Otworz .codeql\*.sarif w Cursor (SARIF Viewer)."
}
