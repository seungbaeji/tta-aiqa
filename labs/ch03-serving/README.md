# 3장 Serving

## 1. 목표

### 1-1. 동일한 API 계약

Compose에서는 local sklearn adapter를, Kubernetes에서는 KServe HTTP adapter를
사용하지만 외부 Risk API 계약은 동일함을 확인합니다.

## 2. Compose 실행

### 2-1. Baseline 시작

```bash
uv run python scripts/publish_model.py baseline --revision v2
docker compose -f deploy/compose/simple-mlops/compose.yaml up -d --build risk-api
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/v1/model
```

`profile`은 `baseline`이어야 합니다.

### 2-2. 정상과 계약 위반 traffic

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm traffic-generator baseline --count 20
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm traffic-generator invalid --count 3
```

첫 command는 200, 두 번째 command는 422 응답을 기록해야 합니다. response artifact는
`artifacts/traffic/` 아래에 생성됩니다.

### 2-3. Notebook

`01_verify_risk_api.ipynb`에서 live API identity, valid/invalid request, request ID와
Kubernetes KServe adapter 설정을 확인합니다. API가 다른 URL에 있으면
`AIQA_RISK_API_URL`을 설정합니다.

## 3. Kubernetes 확인

### 3-1. Desired state

```bash
kubectl config current-context
kubectl kustomize deploy/kubernetes/overlays/baseline >/tmp/tta-aiqa-baseline.yaml
kubectl apply --dry-run=server -f /tmp/tta-aiqa-baseline.yaml
```

실제 Argo CD sync 절차와 개인 URL은 강사가 안내합니다. 수강생은 direct apply로
release를 바꾸지 않습니다. Rendered `model-identity` ConfigMap의
`AIQA_KSERVE_EXPECTED_MODEL_SHA256`과 baseline PVC subPath의 bundle digest가 같은지도
확인합니다. 두 값이 다르면 predictor는 시작 단계에서 실패합니다. `ghcr-pull`은
강사가 namespace에 미리 준비하는 registry Secret이며 수강생의 Grafana Cloud Secret과
별개입니다.

## 4. 완료 기준

### 4-1. 계약

- `/health/ready`와 `/v1/model`에서 baseline identity를 확인합니다.
- 유효 요청은 200, feature 계약 위반은 422를 반환하며 request ID가 응답에 포함됩니다.
- `/metrics`에서 model profile/version/scenario label을 확인합니다.
- Kubernetes Risk API가 내부 KServe endpoint를 사용함을 확인합니다.
