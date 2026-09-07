# Grafana Dashboard Importer

## 1. 역할

### 1-1. Grafana Cloud adapter

Versioned dashboard JSON에 개인 datasource UID를 바인딩하고 stable UID로 생성 또는 갱신합니다. Alloy telemetry write credential을 사용하지 않습니다.

## 2. 실행

### 2-1. 설정 검사와 import

```bash
uv run --package aiqa-grafana-dashboard-importer aiqa-grafana-dashboard --check
uv run --package aiqa-grafana-dashboard-importer aiqa-grafana-dashboard
```

## 3. Secret

### 3-1. 입력

값은 `.env.grafanacloud` 또는 `/var/run/secrets/aiqa/grafana-dashboard-importer`에서 읽습니다.
Alloy `api-key`와 Dashboard token은 같은 값이 아닙니다. 예시 키 이름은
[`.env.grafanacloud.example`](../../.env.grafanacloud.example)을 따릅니다.

| 변수 | 어디서 복사하는지 |
|---|---|
| `AIQA_GRAFANA_URL` | Grafana Cloud Portal에서 해당 stack을 Launch한 주소. `https://<stack>.grafana.net` 형태이며 경로와 query를 붙이지 않습니다 |
| `AIQA_GRAFANA_DASHBOARD_PATH` | 이 저장소의 JSON 경로. 기본값은 `deploy/grafana-cloud/dashboards/ai-quality.json`입니다 |
| `AIQA_GRAFANA_DASHBOARD_TOKEN` | Grafana UI Administration → Users and access → Service accounts에서 만든 token. 대시보드 쓰기 권한이 필요합니다. Cloud Access Policy(Alloy write) token을 넣지 않습니다 |
| `AIQA_GRAFANA_FOLDER_UID` | Dashboards에서 수업용 폴더를 연 뒤 Folder settings의 UID. 주소창의 folder UID와 같습니다 |
| `AIQA_GRAFANA_METRICS_DATASOURCE_UID` | Connections → Data sources → Prometheus. Settings의 UID. Grafana Cloud 기본값은 흔히 `grafanacloud-prom`입니다 |
| `AIQA_GRAFANA_LOGS_DATASOURCE_UID` | 같은 화면의 Loki. 흔히 `grafanacloud-logs` |
| `AIQA_GRAFANA_TRACES_DATASOURCE_UID` | 같은 화면의 Tempo. 흔히 `grafanacloud-traces` |

수강생이 화면만 열 때는 import 결과 URL(`/d/tta-aiqa-quality/...`)을
`AIQA_GRAFANA_DASHBOARD_URL`로 받습니다. 이 값은 `.env.grafanacloud`의
`AIQA_GRAFANA_URL`(스택 주소)과 다릅니다. token은 기록하지 않습니다.

Alloy write 값의 복사 위치는
[`deploy/secrets/alloy/README.md`](../../deploy/secrets/alloy/README.md)를
따릅니다.
