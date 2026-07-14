#!/usr/bin/env bash
# Buduje obraz produkcyjny i laduje do k3s (containerd)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
IMAGE_TAG="${IMAGE_TAG:-nc-django-app:test}"

cd "$REPO_ROOT"

echo "Budowanie obrazu $IMAGE_TAG..."
docker build -f deployments/docker/Dockerfile.prod -t "$IMAGE_TAG" .

echo "Import obrazu do k3s..."
docker save "$IMAGE_TAG" | sudo k3s ctr images import -

echo "Obraz $IMAGE_TAG dostepny w klastrze k3s."
