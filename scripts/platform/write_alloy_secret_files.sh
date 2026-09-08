#!/usr/bin/env bash
set -euo pipefail

# Grafana Cloud에서 복사한 값을 아래 따옴표 안에 넣는다.
# 채운 값은 Git에 커밋하지 않는다.
METRICS_URL=""
METRICS_USERNAME=""
LOGS_URL=""
LOGS_USERNAME=""
OTLP_URL=""
OTLP_USERNAME=""
API_KEY=""

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUTPUT_DIR="${1:-"${ROOT}/deploy/secrets/alloy"}"

trim() {
  printf '%s' "$1" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'
}

NAMES=(
  METRICS_URL
  METRICS_USERNAME
  LOGS_URL
  LOGS_USERNAME
  OTLP_URL
  OTLP_USERNAME
  API_KEY
)
FILES=(
  metrics-url
  metrics-username
  logs-url
  logs-username
  otlp-url
  otlp-username
  api-key
)

missing=()
values=()
for name in "${NAMES[@]}"; do
  value="$(trim "${!name:-}")"
  if [ -z "${value}" ]; then
    missing+=("${name}")
  fi
  values+=("${value}")
done

if [ "${#missing[@]}" -ne 0 ]; then
  echo "missing Alloy secret variable: ${missing[*]}" >&2
  exit 2
fi

mkdir -p "${OUTPUT_DIR}"
umask 077
for index in "${!FILES[@]}"; do
  path="${OUTPUT_DIR}/${FILES[$index]}"
  printf '%s\n' "${values[$index]}" > "${path}"
  chmod 600 "${path}"
done
echo "wrote 7 Alloy secret files to ${OUTPUT_DIR}"
