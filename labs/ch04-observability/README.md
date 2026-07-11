# 4장 Observability

## 1. 목표

### 1-1. 개인 Grafana Cloud

각 수강생의 Grafana Cloud stack으로 Risk API logs, metrics와 traces를 보내고 repository의 dashboard를 고정 UID로 생성합니다. Grafana, Loki, Tempo와 Prometheus server를 VM에 설치하지 않습니다.

## 2. 사전 설정

### 2-1. Alloy Secret

`deploy/compose/simple-mlops/secrets/alloy/README.md`에 따라 일곱 개 파일을 만듭니다. Alloy write token과 Dashboard API token은 분리합니다.

### 2-2. Dashboard 설정

```bash
cp .env.grafanacloud.example .env.grafanacloud
```

개인 Grafana URL, Dashboard API token, folder UID와 metrics/logs/traces datasource UID를 `.env.grafanacloud`에 입력합니다. 실제 값은 Git에 추가하지 않습니다.

## 3. 실행

### 3-1. Alloy 연결

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  up -d --build
```

### 3-2. Dashboard import

```bash
uv run --package aiqa-grafana-dashboard-importer aiqa-grafana-dashboard --check
uv run --package aiqa-grafana-dashboard-importer aiqa-grafana-dashboard
```

출력된 dashboard URL을 엽니다. 다시 실행해도 UID `tta-aiqa-quality`의 같은 dashboard가 갱신되어야 합니다.

### 3-3. Notebook

`01_inspect_dashboard_contract.ipynb`에서 telemetry metric과 dashboard query가 일치하는지 확인합니다.

## 4. 완료 기준

### 4-1. Baseline telemetry

- request rate, error rate, latency와 prediction metric이 표시됩니다.
- logs에서 `request_id`, traces에서 같은 요청 흐름을 탐색할 수 있습니다.
- dashboard에 baseline `model_version` 데이터가 쌓입니다.
