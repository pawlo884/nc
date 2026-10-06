#!/usr/bin/env bash
# Deploy produkcji — JEDEN stack docker-compose (zastępuje scripts/k8s-prod/ i
# scripts/deploy/*blue-green*). Patrz docker-compose/docker-compose.prod.yml, #259.
#
# Użycie na VPS:
#   ./scripts/deploy-prod.sh [<ref>]      # ref = tag / branch, domyślnie main
#
# Kroki: git reset --hard <ref> → build obrazu → migracje → up -d → health.
# Kilka sekund 502 na `web` podczas recreate — akceptowalne (bez blue-green).
set -euo pipefail

REF="${1:-main}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CF="$REPO_ROOT/docker-compose/docker-compose.prod.yml"

# Ta sama nazwa projektu co dotychczasowy stack (dir "docker-compose"), żeby
# `up -d` adoptował istniejące kontenery/sieci/wolumeny zamiast tworzyć drugi komplet.
export COMPOSE_PROJECT_NAME=docker-compose

DC() { docker compose -f "$CF" "$@"; }

cd "$REPO_ROOT"

echo "📥 Pobieram $REF"
git fetch origin --tags --prune
if git rev-parse --verify "origin/$REF" >/dev/null 2>&1; then
  git reset --hard "origin/$REF"
elif git rev-parse --verify "$REF" >/dev/null 2>&1; then
  git reset --hard "$REF"
else
  echo "❌ Ref '$REF' nie istnieje"; exit 1
fi
echo "📌 $(git rev-parse --short HEAD) — $(git log -1 --pretty=%s)"

[[ -f "$REPO_ROOT/.env.prod" ]] || { echo "❌ Brak .env.prod na serwerze"; exit 1; }

echo "🔨 Buduję obraz nc-django-app:latest"
DC build

echo "🗃️  Migracje (stary web nadal obsługuje ruch)"
DC --profile migrate run --rm migrate

echo "🚀 up -d (recreate)"
DC up -d --remove-orphans

echo "🩺 Health check web"
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8000/health/ >/dev/null; then
    echo "✅ web zdrowy ($(git rev-parse --short HEAD))"
    DC ps
    exit 0
  fi
  sleep 2
done

echo "❌ Health check nie przeszedł w 60 s"
DC logs --tail=50 web
exit 1
