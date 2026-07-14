#!/usr/bin/env bash
# Wspolna konfiguracja kubectl dla skryptow k8s-prod
set -euo pipefail

export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"

if [[ ! -f "$KUBECONFIG" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  "$SCRIPT_DIR/setup-kubeconfig.sh"
fi

if ! kubectl cluster-info &>/dev/null; then
  echo "kubectl nie laczy sie z klastrem (KUBECONFIG=$KUBECONFIG)"
  echo "Sprawdz: sudo systemctl status k3s"
  exit 1
fi
