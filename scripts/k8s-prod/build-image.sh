#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
IMAGE_TAG="${IMAGE_TAG:-nc-django-app:latest}"
BUILD_DATE="${BUILD_DATE:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"

cd "$REPO_ROOT"

echo "Budowanie obrazu $IMAGE_TAG..."
docker build -f deployments/docker/Dockerfile.prod \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  -t "$IMAGE_TAG" .

echo "Import obrazu do k3s..."
docker save "$IMAGE_TAG" | sudo k3s ctr images import -

echo "Obraz $IMAGE_TAG dostepny w klastrze."
