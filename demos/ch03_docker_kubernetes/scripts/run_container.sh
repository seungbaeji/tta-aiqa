#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-ai-quality-serving}"
IMAGE_TAG="${IMAGE_TAG:-chapter-03}"
CONTAINER_NAME="${CONTAINER_NAME:-ai-quality-serving}"
HOST_PORT="${HOST_PORT:-8000}"

docker run --rm \
  --name "${CONTAINER_NAME}" \
  -p "${HOST_PORT}:8000" \
  -e MODEL_VERSION="${MODEL_VERSION:-v1}" \
  -e MODEL_THRESHOLD="${MODEL_THRESHOLD:-0.5}" \
  "${IMAGE_NAME}:${IMAGE_TAG}"
