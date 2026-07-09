#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_FILE="${ROOT_DIR}/argocd/application.yaml"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required to register the Argo CD Application." >&2
  exit 1
fi

if grep -q "REPLACE_WITH_COURSE_GIT_REPO_URL" "${APP_FILE}"; then
  echo "Edit ${APP_FILE} and replace REPLACE_WITH_COURSE_GIT_REPO_URL before live registration." >&2
  exit 2
fi

echo "[apply] Register Argo CD Application"
kubectl apply -f "${APP_FILE}"

echo "[next] Inspect with: argocd app get ai-quality-risk-classifier"
