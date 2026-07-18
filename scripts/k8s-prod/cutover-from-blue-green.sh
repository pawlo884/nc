#!/usr/bin/env bash
# Przelaczenie NPM z nginx-router (blue-green) na k3s Traefik
# Uruchom PO udanym deploy.sh i tescie health przez Traefik
set -euo pipefail

echo "=== Sprawdzanie k3s nc-prod ==="
kubectl get pods -n nc-prod -l app=nc-web
kubectl get ingress -n nc-prod

echo ""
echo "Test lokalny Traefik:"
curl -sf -H "Host: nc.sowa.ch" http://127.0.0.1/health/ && echo " OK" || {
  echo "FAIL — napraw k3s przed przelaczeniem NPM"
  exit 1
}

echo ""
echo "=== Zatrzymanie blue-green (bez postgres/redis) ==="
COMPOSE_FILE="docker-compose/docker-compose.blue-green.yml"
if [[ -f "$COMPOSE_FILE" ]]; then
  docker compose -f "$COMPOSE_FILE" stop web-blue web-green nginx-router celery-default celery-import celery-beat flower 2>/dev/null || true
  echo "Kontenery blue-green zatrzymane."
else
  echo "Brak $COMPOSE_FILE — pominieto stop Docker."
fi

echo ""
echo "=== Nastepny krok reczny w NPM ==="
echo "1. Proxy Host nc.sowa.ch -> IP tego serwera, port 30080 (Traefik NodePort)"
echo "2. Proxy Host flower.nc.sowa.ch -> ten sam IP, port 30080"
echo "3. Wylacz forward na nc-nginx-router"
echo "4. Sprawdz https://nc.sowa.ch/health/"
