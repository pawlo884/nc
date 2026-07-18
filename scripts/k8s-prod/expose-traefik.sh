#!/usr/bin/env bash
# Wystaw Traefik (k3s) na NodePort — NPM forwarduje nc.sowa.ch -> IP:30080
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=ensure-kubectl.sh
source "$SCRIPT_DIR/ensure-kubectl.sh"

NODE_PORT_HTTP="${TRAEFIK_NODE_PORT_HTTP:-30080}"
NODE_PORT_HTTPS="${TRAEFIK_NODE_PORT_HTTPS:-30443}"

echo "=== Traefik NodePort ${NODE_PORT_HTTP}/${NODE_PORT_HTTPS} ==="
kubectl patch svc traefik -n kube-system --type='json' -p="[
  {\"op\":\"replace\",\"path\":\"/spec/type\",\"value\":\"NodePort\"},
  {\"op\":\"replace\",\"path\":\"/spec/ports/0/nodePort\",\"value\":${NODE_PORT_HTTP}},
  {\"op\":\"replace\",\"path\":\"/spec/ports/1/nodePort\",\"value\":${NODE_PORT_HTTPS}}
]"

kubectl get svc traefik -n kube-system
echo ""
echo "Test: curl -H 'Host: nc.sowa.ch' http://127.0.0.1:${NODE_PORT_HTTP}/health/"
