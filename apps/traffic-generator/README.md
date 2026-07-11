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
