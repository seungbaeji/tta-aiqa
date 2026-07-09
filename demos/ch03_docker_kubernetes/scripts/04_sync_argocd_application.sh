#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${ARGOCD_APP_NAME:-ai-quality-risk-classifier}"

if ! command -v argocd >/dev/null 2>&1; then
  echo "argocd CLI is required for live diff/sync." >&2
  echo "Fallback: inspect demos/ch03_docker_kubernetes/argocd/application.yaml and gitops/overlays/dev." >&2
  exit 1
fi

echo "[status] Argo CD Application"
argocd app get "${APP_NAME}"

echo "[diff] Desired Git state vs live cluster"
argocd app diff "${APP_NAME}" || true

echo "[sync] Apply desired Git state through Argo CD"
argocd app sync "${APP_NAME}"

echo "[wait] Wait for health and sync"
argocd app wait "${APP_NAME}" --health --sync --timeout 180
