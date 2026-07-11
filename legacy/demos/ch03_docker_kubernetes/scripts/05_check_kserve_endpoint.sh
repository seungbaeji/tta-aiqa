#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${KSERVE_NAMESPACE:-ai-quality}"
SERVICE_NAME="${KSERVE_SERVICE_NAME:-ai-quality-risk-classifier-dev}"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required for live KServe status checks." >&2
  exit 1
fi

echo "[status] KServe InferenceService"
kubectl get inferenceservice "${SERVICE_NAME}" -n "${NAMESPACE}" -o wide

echo "[describe] Predictor and runtime events"
kubectl describe inferenceservice "${SERVICE_NAME}" -n "${NAMESPACE}"
