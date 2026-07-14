#!/usr/bin/env bash
# Deploy produkcji na k3s (zamiast blue-green)
# Uzycie: ./scripts/k8s-prod/deploy.sh [--migrate]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=ensure-kubectl.sh
source "$SCRIPT_DIR/ensure-kubectl.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MANIFEST_DIR="$REPO_ROOT/deployments/k8s/nc-prod"
RUN_MIGRATE=false

for arg in "$@"; do
  case "$arg" in
    --migrate) RUN_MIGRATE=true ;;
  esac
done

cd "$REPO_ROOT"

ENV_FILE="${ENV_FILE:-$REPO_ROOT/.env.prod}"

echo "=== Namespace nc-prod ==="
kubectl apply -f "$MANIFEST_DIR/00-namespace.yaml"

if ! kubectl get secret nc-env -n nc-prod &>/dev/null; then
  if [[ -f "$ENV_FILE" ]]; then
    echo "Brak secret nc-env — tworze z $ENV_FILE..."
    "$SCRIPT_DIR/create-secret.sh"
  else
    echo "Brak secret nc-env i brak pliku $ENV_FILE"
    echo "Utworz .env.prod na serwerze, potem: ./scripts/k8s-prod/create-secret.sh"
    exit 1
  fi
fi

echo "=== Apply manifestow nc-prod ==="
kubectl apply -f "$MANIFEST_DIR/redis.yaml"
kubectl apply -f "$MANIFEST_DIR/web.yaml"
kubectl apply -f "$MANIFEST_DIR/celery.yaml"
kubectl apply -f "$MANIFEST_DIR/ingress.yaml"

if [[ "$RUN_MIGRATE" == true ]]; then
  echo "=== Job migracji ==="
  kubectl delete job nc-migrate -n nc-prod --ignore-not-found
  kubectl apply -f "$MANIFEST_DIR/migrate-job.yaml"
  kubectl wait --for=condition=complete job/nc-migrate -n nc-prod --timeout=600s
  kubectl logs job/nc-migrate -n nc-prod
fi

echo "=== Rollout nc-web ==="
if kubectl get deployment nc-web -n nc-prod &>/dev/null; then
  kubectl rollout restart deployment/nc-web -n nc-prod
  kubectl rollout status deployment/nc-web -n nc-prod --timeout=600s
else
  echo "Pierwszy deploy — czekam na utworzenie deployment nc-web..."
  kubectl rollout status deployment/nc-web -n nc-prod --timeout=600s
fi
kubectl rollout restart deployment/celery-default deployment/celery-import deployment/celery-beat -n nc-prod 2>/dev/null || true

POD_COUNT="$(kubectl get pods -n nc-prod --no-headers 2>/dev/null | wc -l | tr -d ' ')"
if [[ "${POD_COUNT:-0}" -lt 1 ]]; then
  echo "BLAD: Brak podow w nc-prod po deploy!"
  kubectl get events -n nc-prod --sort-by='.lastTimestamp' | tail -20
  exit 1
fi

echo ""
kubectl get pods,svc,ingress -n nc-prod
echo ""
echo "Health: curl -H 'Host: nc.sowa.ch' http://127.0.0.1/health/"
