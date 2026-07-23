# Traffic Generator

## 1. 역할

### 1-1. 독립 process

Operational patient pool에서 deterministic sample을 선택해 baseline, approved-candidate, current-shift와 invalid 요청을 Risk API로 보냅니다. 모델을 import하거나 직접 호출하지 않습니다.

## 2. 실행

### 2-1. Compose

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm traffic-generator baseline --count 20
```

## 3. 설정

### 3-1. Scenario

요청 수, seed와 transform은 `configs/traffic/scenarios.yaml`에서 관리합니다. 응답 기록은 `artifacts/traffic`에 생성합니다.

## 4. Trace 계약

`main`은 scenario 실행 전체에 `traffic.generate` root span을 엽니다. 각
`/v1/predict` 요청은 `risk-api.predict` CLIENT span 안에서 전송되며, 그 span의
W3C `traceparent`, `X-Request-ID`, `X-AIQA-Scenario`가 Risk API에 전달됩니다.

- 하나의 scenario 실행에는 여러 prediction 요청이 있으므로 root span 아래에 요청별 CLIENT span이 생깁니다.
- request ID와 trace ID는 응답, JSON log와 trace를 연결하는 값입니다. 이 process는 scrape metric을 노출하지 않으며, 식별자를 Prometheus label로 사용하지 않습니다.
