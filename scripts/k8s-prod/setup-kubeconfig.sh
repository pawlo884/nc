#!/usr/bin/env bash
# Jednorazowa konfiguracja kubectl dla uzytkownika (k3s domyslnie: tylko root)
set -euo pipefail

KUBECONFIG_PATH="${KUBECONFIG:-$HOME/.kube/config}"

mkdir -p "$(dirname "$KUBECONFIG_PATH")"
sudo k3s kubectl config view --raw > "$KUBECONFIG_PATH"
chmod 600 "$KUBECONFIG_PATH"

echo "Kubeconfig zapisany: $KUBECONFIG_PATH"
echo ""
echo "Dodaj do ~/.bashrc (opcjonalnie, trwale):"
echo "  export KUBECONFIG=$KUBECONFIG_PATH"
echo ""
echo "Test:"
KUBECONFIG="$KUBECONFIG_PATH" kubectl get nodes
