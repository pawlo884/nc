#!/usr/bin/env bash
# Diagnostyka namespace nc-prod
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=ensure-kubectl.sh
source "$SCRIPT_DIR/ensure-kubectl.sh"

echo "=== Namespace nc-prod ==="
kubectl get namespace nc-prod 2>/dev/null || echo "Brak namespace nc-prod"

echo ""
echo "=== Wszystkie zasoby ==="
kubectl get all,ingress,secret -n nc-prod 2>/dev/null || echo "Brak zasobow w nc-prod"

echo ""
echo "=== Events (ostatnie) ==="
kubectl get events -n nc-prod --sort-by='.lastTimestamp' 2>/dev/null | tail -15 || true

echo ""
echo "=== Obraz nc-django-app w k3s ==="
sudo k3s ctr images ls | grep nc-django-app || echo "Brak obrazu nc-django-app:latest w k3s"
