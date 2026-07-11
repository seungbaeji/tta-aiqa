# Risk API

## 1. 역할

### 1-1. Inbound API

Feature contract를 검증하고 mortality-risk score, threshold와 prediction을 반환합니다. Compose에서는 local sklearn, Kubernetes에서는 KServe HTTP adapter를 사용합니다.

## 2. 실행

### 2-1. 권장 경로

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml up -d --build
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/v1/model
```

## 3. Runtime 계약

### 3-1. Endpoint

- `/health/live`: process 상태
- `/health/ready`: model backend readiness
- `/v1/model`: profile, version, threshold
- `/v1/predict`: prediction
- `/metrics`: Prometheus exposition
