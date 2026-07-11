#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_FILE="${ROOT_DIR}/argocd/application.yaml"
OVERLAY_DIR="${ROOT_DIR}/gitops/overlays/student"

echo "[check] Argo CD Application manifest"
test -f "${APP_FILE}"
grep -q "kind: Application" "${APP_FILE}"
grep -q "path: demos/ch03_docker_kubernetes/gitops/overlays/student" "${APP_FILE}"

echo "[check] Kustomize overlay files"
test -f "${OVERLAY_DIR}/kustomization.yaml"
test -f "${ROOT_DIR}/gitops/base/mlflow-tracking.yaml"
test -f "${ROOT_DIR}/gitops/base/mlflow-ingress.yaml"
test -f "${ROOT_DIR}/gitops/base/inferenceservice.yaml"
test -f "${ROOT_DIR}/gitops/base/observability-config.yaml"
test -f "${OVERLAY_DIR}/ingress-host-patch.yaml"

if [[ "${CHECK_LIVE_KUBECTL:-0}" == "1" ]] && command -v kubectl >/dev/null 2>&1; then
  echo "[dry-run] Validate Argo CD Application shape with kubectl client dry-run"
  kubectl apply --dry-run=client --validate=false -f "${APP_FILE}" >/dev/null
elif command -v kubectl >/dev/null 2>&1; then
  echo "[skip] kubectl live-context validation disabled; set CHECK_LIVE_KUBECTL=1 to enable"
else
  echo "[skip] kubectl is not installed; manifest file inspection completed"
fi

if command -v kustomize >/dev/null 2>&1; then
  echo "[render] kustomize build ${OVERLAY_DIR}"
  kustomize build "${OVERLAY_DIR}" >/tmp/ai-quality-kserve-rendered.yaml
  grep -q "kind: Deployment" /tmp/ai-quality-kserve-rendered.yaml
  grep -q "name: mlflow-tracking" /tmp/ai-quality-kserve-rendered.yaml
  grep -q "kind: Ingress" /tmp/ai-quality-kserve-rendered.yaml
  grep -q "kind: InferenceService" /tmp/ai-quality-kserve-rendered.yaml
  if grep -q "REPLACE_WITH_YOUR_INGRESS_DOMAIN" /tmp/ai-quality-kserve-rendered.yaml; then
    echo "[warn] Ingress host still has the course placeholder. Edit ${OVERLAY_DIR}/ingress-host-patch.yaml before live sync."
  fi
else
  echo "[skip] kustomize is not installed; overlay file inspection completed"
fi

echo "[done] Argo CD/KServe manifest inspection completed"
