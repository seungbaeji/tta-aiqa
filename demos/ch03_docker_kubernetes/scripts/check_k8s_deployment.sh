#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-ai-quality}"
DEPLOYMENT="${DEPLOYMENT:-ai-quality-serving}"
SERVICE="${SERVICE:-ai-quality-serving}"

kubectl -n "${NAMESPACE}" rollout status deployment/"${DEPLOYMENT}"
kubectl -n "${NAMESPACE}" get pods -l app="${SERVICE}"
kubectl -n "${NAMESPACE}" get service "${SERVICE}"
echo
echo "To smoke-test the API, run:"
echo "kubectl -n ${NAMESPACE} port-forward service/${SERVICE} 8000:80"
echo "bash demos/ch03_docker_kubernetes/scripts/check_container.sh"
