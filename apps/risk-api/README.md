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

## 4. Trace와 metric 경계

`/v1/predict`는 FastAPI HTTP SERVER span 아래에서 `risk.predict` operation을
수행합니다. Kubernetes에서 KServe backend를 선택하면 이 operation 안에서
`kserve.infer` CLIENT span을 열고, 그 span의 W3C context와 request ID를 KServe로
전달합니다.

- `/v1/predict`만 Risk API의 business metric 대상입니다. `/health/*`와 `/metrics`는 business metric을 만들지 않고 trace도 남기지 않습니다.
- `trace_id`는 JSON log와 trace 탐색을 연결할 때만 사용합니다. request ID, run ID, trace ID, span ID는 Prometheus metric label이 아닙니다.
