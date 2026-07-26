# 요청 생성기

## 1. 역할

### 1-1. 별도 실행 프로그램

정답이 없는 운영 표본에서 고정된 난수로 같은 행 순서를 선택해 `baseline`,
`approved-candidate`, `current-shift`, `invalid` 요청을 Risk API로 보냅니다.
모델 코드를 가져오거나 모델을 직접 호출하지 않습니다.

## 2. 실행

### 2-1. 로컬 API만 빠르게 확인

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm traffic-generator baseline --count 20 --fast
```

`--fast`는 로컬 API 응답만 빠르게 확인합니다. 이 결과를 Grafana의 `rate()`
근거로 쓰지 않습니다. Grafana 실습에서는 Alloy 추가 설정을 함께 적용하고
`--fast`를 빼야 합니다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  --profile traffic run --rm traffic-generator baseline
```

## 3. 설정

### 3-1. 시나리오

요청 수, 난수 초깃값, 요청 간격, 수집 대기 시간과 입력 변환은
`configs/traffic/scenarios.yaml`에서 관리합니다. 기본 관측 실행은 15초 수집
주기 사이에서 값이 두 번 이상 달라지도록 요청을 보내고, 마지막 요청 뒤 20초를
더 기다립니다. 첫 수집 전에 이미 끝난 요청은 나중에 복원할 수 없으므로 요청
구간 자체도 15초보다 길게 유지합니다.

표본을 고르는 난수에는 시나리오와 실행 ID를 섞지 않습니다. 따라서 `baseline`과
`current-shift`는 같은 환자 순서를 사용하고, 후자에만 선언된 변환을 적용합니다.
실행마다 새 실행 ID가 생기므로 다시 실행해도 요청 ID가 충돌하지 않습니다. 출력된
실행 ID와 `artifacts/traffic/compose.jsonl`의 `run_id`를 판단 기록에 옮깁니다.

## 4. 추적 규약

한 시나리오를 실행하면 `traffic.generate` 최상위 span이 열립니다. 각
`/v1/predict` 요청은 `risk-api.predict` CLIENT span 안에서 전송되며 W3C
`traceparent`, `X-Request-ID`, `X-AIQA-Run-ID`, `X-AIQA-Scenario`가 Risk API로
전달됩니다.

- 한 시나리오에는 여러 예측 요청이 있으므로 최상위 span 아래에 요청별 CLIENT
  span이 생깁니다.
- 실행 ID는 한 번의 실행 묶음을, 요청 ID는 그 안의 요청 하나를 연결합니다. 이 두
  값과 trace ID는 JSONL, 구조화 로그와 trace에서만 사용하며 Prometheus
  레이블로 사용하지 않습니다.
