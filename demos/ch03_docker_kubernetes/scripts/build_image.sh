#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-ai-quality-serving}"
IMAGE_TAG="${IMAGE_TAG:-chapter-03}"
MODEL_PATH="${MODEL_PATH:-artifacts/models/chapter_02_baseline.pkl}"

if [[ ! -f "${MODEL_PATH}" ]]; then
  echo "Model artifact not found: ${MODEL_PATH}" >&2
  echo "Run: uv run --group lab python labs/ch02_model_quality/train_baseline.py" >&2
  exit 1
fi

docker build \
  -f demos/ch03_docker_kubernetes/Dockerfile \
  -t "${IMAGE_NAME}:${IMAGE_TAG}" \
  .
