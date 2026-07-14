#!/usr/bin/env bash
# Tworzy Secret nc-env w namespace nc-test z pliku .env.test
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/.env.test}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Brak pliku $ENV_FILE — skopiuj docs/env.test.sample.md i uzupelnij."
  exit 1
fi

kubectl create namespace nc-test --dry-run=client -o yaml | kubectl apply -f -
kubectl delete secret nc-env -n nc-test --ignore-not-found
kubectl create secret generic nc-env --from-env-file="$ENV_FILE" -n nc-test
echo "Secret nc-env utworzony w namespace nc-test."
