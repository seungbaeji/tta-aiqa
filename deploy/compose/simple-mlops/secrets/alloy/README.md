## 1. 로컬 Docker Compose용 Alloy 설정

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

여기까지는 로컬 Docker Compose가 읽을 파일을 준비하는 절차다. 파일을
작성하거나 권한을 `600`으로 바꾸는 작업은 Kubernetes 클러스터를 변경하지
않는다.

## 2. Kubernetes Secret 준비

Kubernetes Secret 생성은 로컬 파일 준비와 달리 대상 클러스터를 변경한다.
클러스터 운영자가 승인한 정확한 context를 `TARGET_CONTEXT`에 설정한 뒤,
이 디렉터리에서 아래 명령을 실행한다. 값이 비었거나 현재 context와 다르면
클러스터에 요청을 보내기 전에 중단한다.

```bash
if [ -z "${TARGET_CONTEXT:-}" ]; then
  echo "TARGET_CONTEXT가 비어 있어 Secret 생성을 중단합니다." >&2
  exit 1
fi
CURRENT_CONTEXT="$(kubectl config current-context)" || {
  echo "현재 context를 확인할 수 없어 Secret 생성을 중단합니다." >&2
  exit 1
}
if [ "$CURRENT_CONTEXT" != "$TARGET_CONTEXT" ]; then
  echo "지정된 대상 context가 아니므로 중단합니다: $CURRENT_CONTEXT" >&2
  exit 1
fi
kubectl --context "$TARGET_CONTEXT" -n tta-aiqa \
  create secret generic alloy-grafana-cloud \
  --from-file=metrics-url \
  --from-file=metrics-username \
  --from-file=logs-url \
  --from-file=logs-username \
  --from-file=otlp-url \
  --from-file=otlp-username \
  --from-file=api-key
```
