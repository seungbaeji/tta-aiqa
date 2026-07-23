# 4장 운영 상태 확인

## 1. 목표와 확인 범위

이 실습은 Grafana 화면을 여는 데서 끝나지 않습니다. 대시보드 조회식, 요청 시나리오, 모델 정보, 조회 시간 범위를 연결해 입력, API, 실행 환경 가운데 어떤 원인 후보를 더 확인해야 하는지 기록합니다.

운영 요청에는 정답이 없으므로 점수나 예측 비율이 달라져도 Candidate B의 재현율, 정밀도, 미탐 수를 다시 계산하지 않습니다. 운영 신호는 원인 후보를 강화하거나 약화하는 근거이며 모델 결함과 단일 원인을 확정하는 자료가 아닙니다.

Grafana Cloud 접속 정보, Alloy 비밀값, Docker가 없으면 노트북의 정적 계약을 확인하고 실시간 운영 자료를 보지 못했다고 기록합니다. 확인하지 않은 대시보드 URL, 화면, 수집 성공을 완료 결과로 쓰지 않습니다.

## 2. Grafana Cloud와 Alloy 준비

`deploy/compose/simple-mlops/secrets/alloy/README.md`에 따라 일곱 개의 비밀값 파일을 만듭니다. Alloy 전송 토큰과 대시보드 API 토큰은 권한이 다르므로 분리합니다.

개인 Grafana URL, 대시보드 API 토큰, 폴더 UID, 지표, 로그, 추적 데이터 소스 UID를 `.env.grafanacloud`에 입력합니다. 실제 값은 Git에 추가하지 않습니다.

```bash
cp .env.grafanacloud.example .env.grafanacloud
uv run --package aiqa-grafana-dashboard-importer aiqa-grafana-dashboard --check
```

`--check`가 빠진 설정을 알려 주면 예상한 준비 상태입니다. 이 출력은 대시보드 가져오기나 실시간 수집이 성공했다는 뜻이 아닙니다.

## 3. 대시보드 계약과 실제 요청 확인

`01_inspect_dashboard_contract.ipynb`는 대시보드 UID `tta-aiqa-quality`, Risk API가 제공하는 다섯 `aiqa_risk_*` 지표, Prometheus, Loki, Tempo 데이터 소스와 로컬 `/metrics` 대체 경로를 확인합니다. 정적 검사가 통과해도 Grafana Cloud가 실제 자료를 수집했다는 뜻은 아닙니다.

Docker, Alloy, 개인 Grafana Cloud 설정이 준비된 경우에만 다음 경로를 실행합니다. 기준 조건, 변화 조건, 무효 요청을 서로 다른 시간대에 보내고 시작, 종료 시각을 기록합니다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  up -d --build
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm traffic-generator baseline --count 20
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm traffic-generator current-shift --count 20
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm traffic-generator invalid --count 3
uv run --package aiqa-grafana-dashboard-importer aiqa-grafana-dashboard
```

출력된 대시보드 URL에서 환경, 모델 프로필과 버전, 시나리오, 시간 범위, 요청 상태 구성, P95 지연 시간, 점수, 예측, 결측 신호, 대표 요청 ID를 확인합니다. 다시 가져와도 같은 UID의 대시보드가 갱신되어야 합니다.

`invalid` 요청은 HTTP 422를 의도적으로 만듭니다. 422는 상태 코드별 요청 건수에서 확인하고, 5xx만 집계하는 오류율과 구분합니다. 5xx 패널에 422가 없다는 사실을 입력 검증 실패가 없었다고 해석하지 않습니다.

### Trace 확인

대표 요청 하나는 로그의 `request_id` 또는 `trace_id`로 Tempo에서 찾습니다. 다음 parent-child 순서를 확인합니다.

- Compose: `traffic.generate` -> `risk-api.predict` (CLIENT) -> `POST /v1/predict` (SERVER) -> `risk.predict`
- Kubernetes KServe: `risk.predict` -> `kserve.infer` (Risk API CLIENT) -> KServe HTTP SERVER -> `kserve.infer`

- `/health/*`, `/metrics`, KServe readiness는 반복 probe이므로 trace에 의도적으로 나타나지 않습니다.
- trace ID는 로그와 trace를 연결하는 값이며 Prometheus metric label이나 집계 조건으로 사용하지 않습니다.
- 한 요청의 trace를 확인해도 Grafana Cloud 전체 수집 성공을 단정하지 않습니다. 시간 범위와 환경을 함께 기록합니다.

## 4. 완료 기준과 정리

최종 기록에는 환경, 시간 범위, 모델 정보, 시나리오, 관측한 신호, 강화된 원인 후보, 아직 확정할 수 없는 내용을 적습니다. 실시간 자료를 보지 못했다면 필요한 설정과 담당 팀을 함께 남깁니다.

> [환경과 시간 범위]에서 [모델 프로필, 버전, 시나리오]의 [상태, 지연, 점수, 예측, 결측 신호]를 [대시보드 URL 또는 API 지표]에서 확인했습니다. 이 신호는 [입력/API/실행 환경 원인 후보]를 강화하지만, 정답 기반 모델 지표와 단일 원인은 아직 확정하지 않습니다. [담당 팀]이 [필요한 자료]를 수집하면 현재 운영 권고를 다시 판단합니다.

본인이 시작했고 다음 실습에 필요하지 않은 Compose 작업만 정리합니다. 다른 수강생이나 강사가 이미 시작한 작업은 종료하지 않습니다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  down
```
