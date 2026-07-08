#!/usr/bin/env bash

set -euo pipefail

CONTAINER_NAME="ai-mlflow"
HOST_PORT="${MLFLOW_PORT:-5001}"
IMAGE="${MLFLOW_IMAGE:-ghcr.io/mlflow/mlflow:latest}"
ARTIFACT_DIR="$(pwd)/artifacts/mlflow"
STARTUP_WAIT_SECONDS="${MLFLOW_STARTUP_WAIT_SECONDS:-3}"
RETRY_TRIES="${MLFLOW_READY_RETRIES:-20}"

function is_port_in_use() {
  local port=$1
  lsof -nP -iTCP:${port} -sTCP:LISTEN >/dev/null 2>&1
}

function find_free_port() {
  local port=$1
  while is_port_in_use "$port"; do
    port=$((port + 1))
  done
  echo "$port"
}

function is_mlflow_ready() {
  local port=$1
  local status
  status="$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:${port}/" 2>/dev/null || true)"
  [ "$status" = "200" ]
}

function start_container() {
  local mapped_port=$1
  echo "Creating and starting MLflow container: ${CONTAINER_NAME}"
  docker run -d --name "${CONTAINER_NAME}" \
    -p "${mapped_port}:5000" \
    -v "${ARTIFACT_DIR}:/mlflow" \
    "${IMAGE}" \
    mlflow server \
      --backend-store-uri sqlite:////mlflow/mlflow.db \
      --default-artifact-root /mlflow/artifacts \
      --host 0.0.0.0 \
      --port 5000
}

mkdir -p "$ARTIFACT_DIR/artifacts"
HOST_PORT="$(find_free_port "$HOST_PORT")"

if docker ps --filter "name=^${CONTAINER_NAME}$" --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  CONTAINER_PORT="$(docker port "${CONTAINER_NAME}" 5000/tcp | head -n 1 | awk -F ':' '{print $NF}')"
  CONTAINER_PORT="${CONTAINER_PORT:-$HOST_PORT}"
  echo "MLflow container is already running: ${CONTAINER_NAME} (mapped port: ${CONTAINER_PORT})"
else
  if docker ps -a --filter "name=^${CONTAINER_NAME}$" --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Removing stale container: ${CONTAINER_NAME}"
    docker rm -f "${CONTAINER_NAME}" >/dev/null
  fi
  CONTAINER_PORT="$HOST_PORT"
  start_container "$CONTAINER_PORT" >/dev/null
fi

# 포트가 이미 사용 중이어서 AirPlay 등에서 훔쳐먹는 상황을 피하기 위해
# 200/루트 응답이 나올 때까지 대기 후, 실패하면 포트를 바꿔 재시도
if ! is_mlflow_ready "$CONTAINER_PORT"; then
  echo "MLflow is not ready on port ${CONTAINER_PORT}. Recreating container..."
  docker rm -f "${CONTAINER_NAME}" >/dev/null
  HOST_PORT="$(find_free_port 5001)"
  CONTAINER_PORT="$HOST_PORT"
  start_container "$CONTAINER_PORT" >/dev/null
fi

sleep "$STARTUP_WAIT_SECONDS"

ready=0
if ! is_mlflow_ready "$CONTAINER_PORT"; then
  for _ in $(seq 1 "$RETRY_TRIES"); do
    if is_mlflow_ready "$CONTAINER_PORT"; then
      ready=1
      break
    fi
    sleep 1
  done
  if [ "$ready" -ne 1 ]; then
    echo "MLflow did not become ready. Check logs: docker logs ${CONTAINER_NAME}"
    exit 1
  fi
fi

TRACKING_URI="http://127.0.0.1:${CONTAINER_PORT}"

if [ "${CONTAINER_PORT}" != "${HOST_PORT}" ]; then
  echo "MLflow container is running on port ${CONTAINER_PORT}"
fi

MLFLOW_TRACKING_URI="${TRACKING_URI}" \
  uv run --group demo python demos/ch02_mlflow/run_demo.py

echo "If you need to remove the container:"
echo "docker stop ${CONTAINER_NAME} && docker rm ${CONTAINER_NAME}"
