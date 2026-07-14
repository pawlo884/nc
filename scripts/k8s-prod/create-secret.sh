#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=ensure-kubectl.sh
source "$SCRIPT_DIR/ensure-kubectl.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/.env.prod}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Brak pliku $ENV_FILE"
  exit 1
fi

kubectl create namespace nc-prod --dry-run=client -o yaml | kubectl apply -f -
kubectl delete secret nc-env -n nc-prod --ignore-not-found
kubectl create secret generic nc-env --from-env-file="$ENV_FILE" -n nc-prod
echo "Secret nc-env utworzony w namespace nc-prod."
