# 3장 Serving

## 1. 목표

### 1-1. 동일한 API

Compose에서는 local sklearn adapter를, Kubernetes에서는 KServe HTTP adapter를 사용하지만 외부 Risk API 계약은 동일함을 확인합니다.

## 2. Compose 실행

### 2-1. Baseline 시작

```bash
uv run python scripts/publish_model.py baseline --revision v2
docker compose -f deploy/compose/simple-mlops/compose.yaml up -d --build
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/v1/model
```

`profile`은 `baseline`이어야 합니다.

### 2-2. Traffic

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm traffic-generator baseline --count 20
```

### 2-3. Notebook

`01_verify_risk_api.ipynb`에서 live API identity와 Kubernetes KServe adapter 설정을 확인합니다. API가 다른 URL에 있으면 `AIQA_RISK_API_URL`을 설정합니다.

## 3. Kubernetes 확인

### 3-1. Manifest

```bash
kubectl kustomize deploy/kubernetes/overlays/baseline >/tmp/tta-aiqa-baseline.yaml
kubectl apply --dry-run=server -f /tmp/tta-aiqa-baseline.yaml
```

실제 Argo CD sync 절차와 개인 URL은 강사가 안내합니다.

## 4. 완료 기준

### 4-1. 계약

- `/health/ready`와 `/v1/model`에서 baseline identity를 확인합니다.
- 유효 요청은 200, feature 계약 위반은 422를 반환합니다.
- Kubernetes Risk API가 내부 KServe endpoint를 사용함을 확인합니다.
