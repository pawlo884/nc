#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=ensure-kubectl.sh
source "$SCRIPT_DIR/ensure-kubectl.sh"
# shellcheck source=prepare-env-for-secret.sh
source "$SCRIPT_DIR/prepare-env-for-secret.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/.env.prod}"
NAMESPACE="${K8S_NAMESPACE:-nc-prod}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Brak pliku $ENV_FILE"
  exit 1
fi

PREPARED_ENV="$(mktemp)"
trap 'rm -f "$PREPARED_ENV"' EXIT

prepare_env_for_k8s_secret "$ENV_FILE" "$PREPARED_ENV"

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
kubectl delete secret nc-env -n "$NAMESPACE" --ignore-not-found
kubectl create secret generic nc-env --from-env-file="$PREPARED_ENV" -n "$NAMESPACE"
echo "Secret nc-env utworzony w namespace $NAMESPACE."
