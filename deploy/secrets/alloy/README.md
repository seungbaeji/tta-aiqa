## 1. 로컬 Docker Compose용 Alloy 설정

이 디렉터리에 다음 파일을 만들고 각 파일에는 값 하나만 저장한다.
값은 Grafana Cloud Portal(`grafana.com`에 로그인한 뒤 해당 stack)에서 복사한다.
화면 이름은 Grafana Cloud가 바꿀 수 있으므로, 아래 공식 문서와 함께 본다.

- `metrics-url`: stack의 Prometheus 카드 Details에 있는 remote write URL (`/api/prom/push`)
- `metrics-username`: 같은 페이지의 User / metrics instance ID
- `logs-url`: stack의 Loki 카드 Details에 있는 Loki push URL
- `logs-username`: 같은 페이지의 User / logs instance ID
- `otlp-url`: stack의 OpenTelemetry 카드 Configure에 있는 OTLP endpoint. `/otlp`로 끝나야 한다
- `otlp-username`: 같은 페이지의 instance ID
- `api-key`: Cloud Portal Security → Access Policies에서 만든 token. `metrics:write`, `logs:write`, `traces:write`(문서의 MetricsPublisher, LogsWriter, TracesWriter)가 필요하다

공식 위치:

- Metrics remote write: <https://grafana.com/docs/grafana-cloud/observe-and-act/send-data/metrics/metrics-prometheus/>
- OTLP: <https://grafana.com/docs/grafana-cloud/observe-and-act/send-data/otlp/send-data-otlp/>
- Access policy token: <https://grafana.com/docs/grafana-cloud/security-and-account-management/authentication-and-permissions/access-policies/create-access-policies/>

이 값들은 Git에 추가하지 않는다. Dashboard API token은 이 디렉터리의
`api-key`와 분리해 Dashboard Importer 설정에만 제공한다.
대시보드 import 값의 복사 위치는
[`apps/grafana_dashboard_importer/README.md`](../../apps/grafana_dashboard_importer/README.md)를
따른다.

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
