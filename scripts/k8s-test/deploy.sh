#!/usr/bin/env bash
# Deploy srodowiska nc-test na k3s
# Uzycie: ./scripts/k8s-test/deploy.sh [--migrate]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MANIFEST_DIR="$REPO_ROOT/deployments/k8s/nc-test"
RUN_MIGRATE=false

for arg in "$@"; do
  case "$arg" in
    --migrate) RUN_MIGRATE=true ;;
  esac
done

cd "$REPO_ROOT"

if ! kubectl get secret nc-env -n nc-test &>/dev/null; then
  echo "Brak secret nc-env — uruchom: ./scripts/k8s-test/create-secret.sh"
  exit 1
fi

echo "=== Apply manifestow nc-test ==="
kubectl apply -f "$MANIFEST_DIR/00-namespace.yaml"
kubectl apply -f "$MANIFEST_DIR/redis.yaml"
kubectl apply -f "$MANIFEST_DIR/web.yaml"
kubectl apply -f "$MANIFEST_DIR/celery.yaml"
kubectl apply -f "$MANIFEST_DIR/ingress.yaml"

if [[ "$RUN_MIGRATE" == true ]]; then
  echo "=== Job migracji ==="
  kubectl delete job nc-migrate -n nc-test --ignore-not-found
  kubectl apply -f "$MANIFEST_DIR/migrate-job.yaml"
  kubectl wait --for=condition=complete job/nc-migrate -n nc-test --timeout=300s
  kubectl logs job/nc-migrate -n nc-test
fi

echo "=== Rollout nc-web ==="
kubectl rollout restart deployment/nc-web -n nc-test
kubectl rollout status deployment/nc-web -n nc-test --timeout=300s

echo ""
kubectl get pods,svc,ingress -n nc-test
echo ""
echo "Test: curl -H 'Host: nc-test.sowa.ch' https://nc-test.sowa.ch/health/"
echo "      (DNS + NPM/Traefik musza wskazywac na klaster k3s)"
