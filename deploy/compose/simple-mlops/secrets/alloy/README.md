## 1. Grafana Cloud Alloy 설정

이 디렉터리에 다음 파일을 만들고 각 파일에는 값 하나만 저장한다.

- `metrics-url`: Prometheus remote write URL
- `metrics-username`: Metrics instance ID
- `logs-url`: Loki push URL
- `logs-username`: Logs instance ID
- `otlp-url`: `/otlp`로 끝나는 OTLP gateway URL
- `otlp-username`: OTLP instance ID
- `api-key`: MetricsPublisher, LogsWriter, TracesWriter 권한의 Alloy access policy token

이 값들은 Git에 추가하지 않는다. Dashboard API token은 이 디렉터리의
`api-key`와 분리해 Dashboard Importer 설정에만 제공한다.

Kubernetes에서는 같은 파일을 사용해 Secret을 만든다.

```bash
kubectl -n tta-aiqa create secret generic alloy-grafana-cloud \
  --from-file=metrics-url \
  --from-file=metrics-username \
  --from-file=logs-url \
  --from-file=logs-username \
  --from-file=otlp-url \
  --from-file=otlp-username \
  --from-file=api-key
```
