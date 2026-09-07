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

Grafana URL, Dashboard API token, folder UID와 세 datasource UID는 `.env.grafanacloud` 또는 `/var/run/secrets/aiqa/grafana-dashboard-importer`에서 읽습니다.
