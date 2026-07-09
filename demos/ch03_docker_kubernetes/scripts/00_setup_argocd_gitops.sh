#!/usr/bin/env bash
set -euo pipefail

COMMAND="${1:-help}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_FILE="${ROOT_DIR}/argocd/application.yaml"
OVERLAY_DIR="${ROOT_DIR}/argocd-resources/overlays/student"
APP_NAME="${ARGOCD_APP_NAME:-ai-quality-risk-classifier}"
REPO_SSH_URL="${ARGOCD_REPO_URL:-git@github.com:seungbaeji/tta-aiqa.git}"
KEY_DIR="${ARGOCD_KEY_DIR:-.argocd}"
KEY_NAME="${ARGOCD_KEY_NAME:-tta-aiqa-argocd-deploy-key}"
KEY_PATH="${ARGOCD_SSH_PRIVATE_KEY:-${KEY_DIR}/${KEY_NAME}}"
KEY_COMMENT="${ARGOCD_KEY_COMMENT:-argocd-tta-aiqa}"

usage() {
  cat <<EOF
Usage: bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh <command>

Commands:
  check    Inspect Argo CD and KServe manifest files without changing the cluster
  key      Generate or reuse a GitHub read-only Deploy key and print the public key
  connect  Register the GitHub repository credential and Argo CD Application
  sync     Run Argo CD diff/sync/wait for the Application

Environment:
  ARGOCD_REPO_URL           Git SSH URL. Default: ${REPO_SSH_URL}
  ARGOCD_SSH_PRIVATE_KEY    Private key path. Default: ${KEY_PATH}
  ARGOCD_APP_NAME           Argo CD app name. Default: ${APP_NAME}

Typical live order:
  1. bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh check
  2. Edit demos/ch03_docker_kubernetes/argocd-resources/overlays/student/ingress-host-patch.yaml
  3. bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh key
  4. Add the printed public key to GitHub repository Deploy keys
  5. bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh connect
  6. bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh sync
EOF
}

check_manifests() {
  echo "[check] Argo CD Application manifest"
  test -f "${APP_FILE}"
  grep -q "kind: Application" "${APP_FILE}"
  grep -q "path: demos/ch03_docker_kubernetes/argocd-resources/overlays/student" "${APP_FILE}"

  echo "[check] Kustomize overlay files"
  test -f "${OVERLAY_DIR}/kustomization.yaml"
  test -f "${ROOT_DIR}/argocd-resources/base/mlflow-tracking.yaml"
  test -f "${ROOT_DIR}/argocd-resources/base/mlflow-ingress.yaml"
  test -f "${ROOT_DIR}/argocd-resources/base/inferenceservice.yaml"
  test -f "${ROOT_DIR}/argocd-resources/base/observability-config.yaml"
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
}

prepare_key() {
  if ! command -v ssh-keygen >/dev/null 2>&1; then
    echo "ssh-keygen is required to create a GitHub Deploy key." >&2
    exit 1
  fi

  mkdir -p "$(dirname "${KEY_PATH}")"
  chmod 700 "$(dirname "${KEY_PATH}")"

  if [[ -f "${KEY_PATH}" || -f "${KEY_PATH}.pub" ]]; then
    echo "[reuse] Deploy key already exists: ${KEY_PATH}"
  else
    echo "[create] Generate read-only GitHub Deploy key pair"
    ssh-keygen -t ed25519 -C "${KEY_COMMENT}" -f "${KEY_PATH}" -N ""
  fi

  chmod 600 "${KEY_PATH}"
  chmod 644 "${KEY_PATH}.pub"

  echo
  echo "[github] Add this public key to the tta-aiqa repository Deploy keys."
  echo "Repository: ${REPO_SSH_URL}"
  echo "GitHub path: Settings -> Deploy keys -> Add deploy key"
  echo "Allow write access: keep unchecked"
  echo
  cat "${KEY_PATH}.pub"
  echo
  echo "[next] After adding the public key in GitHub, run:"
  echo "bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh connect"
}

render_application() {
  local tmp_file
  tmp_file="$(mktemp)"
  awk -v repo="${REPO_SSH_URL}" '{gsub("REPLACE_WITH_COURSE_GIT_REPO_URL", repo); print}' "${APP_FILE}" > "${tmp_file}"
  echo "${tmp_file}"
}

connect_repo_and_app() {
  if ! command -v argocd >/dev/null 2>&1; then
    echo "argocd CLI is required to register repository credentials." >&2
    echo "Fallback: register ${REPO_SSH_URL} in the Argo CD UI with the private key at ${KEY_PATH}." >&2
    exit 1
  fi

  if ! command -v kubectl >/dev/null 2>&1; then
    echo "kubectl is required to register the Argo CD Application." >&2
    exit 1
  fi

  if [[ ! -f "${KEY_PATH}" ]]; then
    echo "Private key not found: ${KEY_PATH}" >&2
    echo "Run: bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh key" >&2
    exit 2
  fi

  echo "[repo] Register GitHub repository credential in Argo CD"
  argocd repo add "${REPO_SSH_URL}" \
    --ssh-private-key-path "${KEY_PATH}" \
    --upsert

  local apply_file="${APP_FILE}"
  local tmp_file=""
  if grep -q "REPLACE_WITH_COURSE_GIT_REPO_URL" "${APP_FILE}"; then
    echo "[render] Replace placeholder repoURL with ${REPO_SSH_URL}"
    tmp_file="$(render_application)"
    apply_file="${tmp_file}"
  fi

  echo "[apply] Register Argo CD Application"
  kubectl apply -f "${apply_file}"

  if [[ -n "${tmp_file}" ]]; then
    rm -f "${tmp_file}"
  fi

  echo "[next] Inspect with: argocd app get ${APP_NAME}"
  echo "[next] Sync with: bash demos/ch03_docker_kubernetes/scripts/00_setup_argocd_gitops.sh sync"
}

sync_app() {
  if ! command -v argocd >/dev/null 2>&1; then
    echo "argocd CLI is required for live diff/sync." >&2
    echo "Fallback: inspect demos/ch03_docker_kubernetes/argocd/application.yaml and argocd-resources/overlays/student." >&2
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
}

case "${COMMAND}" in
  check)
    check_manifests
    ;;
  key)
    prepare_key
    ;;
  connect)
    connect_repo_and_app
    ;;
  sync)
    sync_app
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: ${COMMAND}" >&2
    usage >&2
    exit 64
    ;;
esac
