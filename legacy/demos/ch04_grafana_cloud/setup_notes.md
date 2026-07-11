# Grafana Cloud Demo Notes

Grafana Cloud Demo의 기본 목표는 로컬 산출물을 Cloud 화면에서 조회 가능한 운영 증거로 연결하는 것입니다. 수업 필수 경로는 로컬 payload preview와 dashboard JSON 확인이며, 실제 Cloud 연결은 개인 계정과 토큰이 있을 때만 진행합니다. 계정이 없는 환경에서는 준비된 artifact를 열어 어떤 필드가 운영 화면으로 전달되는지 확인합니다.

## 확인 항목

| 항목 | 확인 내용 |
| --- | --- |
| Logs datasource | Loki datasource 이름과 push endpoint |
| Metrics datasource | Prometheus remote_write endpoint |
| Traces datasource | Tempo OTLP traces endpoint |
| Dashboard import | `artifacts/grafana/ai_quality_overview_dashboard.json`, `artifacts/grafana/ai_quality_details_dashboard.json` |
| Payload preview | `artifacts/grafana/grafana_cloud_payload_preview.json` |
| Local fallback | `artifacts/metrics/chapter_04_anomaly.prom`, `artifacts/reports/chapter_04_validation_failure_examples.md` |
| Distribution trend | `ai_quality_prediction_count`, `ai_quality_score_bucket_count`, `Reference vs Current` distribution panel |
| Trace correlation | `course_trace_id`로 Tempo trace와 Loki 로그 연결 |
| 보안 | API token은 문서나 저장소에 기록하지 않음 |

## Demo 순서

로컬 산출물 생성은 Cloud 연결 전의 필수 확인입니다. Cloud 화면이 비어 있을 때도 이 단계의 파일을 기준으로 데이터 생성 문제인지, 전송 문제인지, 쿼리 문제인지 분리할 수 있습니다.

```bash
uv run --group lab python labs/ch04_observability/04_build_observability_artifacts.py
uv run python demos/ch04_grafana_cloud/01_build_grafana_payload.py
```

실제 Cloud 연결은 세 단계로 나눕니다.

| 단계 | 명령 또는 설정 | 확인할 결과 |
| --- | --- | --- |
| Dashboard import | `python demos/ch04_grafana_cloud/02_import_dashboard.py` | `dashboard_import_result=ok` |
| Alloy collector | `docker compose -f demos/ch04_grafana_cloud/docker-compose.alloy.yml up` | Logs, Metrics, Traces를 Cloud로 전송 |
| Metrics source | `03_serve_metrics.py` | Alloy가 `ai_quality_high_risk_rate`를 scrape |
| Traces sender | `04_send_traces_to_alloy.py` | Alloy OTLP receiver로 span 전송 |
| Streaming sender | `05_stream_observability_to_alloy.py` | 로그, 메트릭, trace를 계속 추가 전송 |

실행 전에는 저장소 루트의 `.env.example`을 참고해 저장소 루트에 `.env`를 만듭니다. Grafana demo 스크립트는 루트 `.env`를 자동으로 읽습니다. 수강생 경로에서는 Logs, Metrics, Traces 각각의 detail 화면에서 URL과 User를 그대로 복사하고, Logs/Metrics/Traces write scope를 가진 access policy token 하나를 `GRAFANA_TELEMETRY_TOKEN`에 넣습니다. `GRAFANA_DASHBOARD_TOKEN`은 Dashboard import API용으로 따로 발급합니다.

```bash
GRAFANA_CLOUD_URL=https://<your-stack>.grafana.net
GRAFANA_TELEMETRY_TOKEN=<access-policy-token-with-logs-metrics-traces-write>
GRAFANA_DASHBOARD_TOKEN=<grafana-service-account-token-for-dashboard-import>
GRAFANA_LOKI_URL=https://logs-prod-<region>.grafana.net
GRAFANA_LOKI_PUSH_URL=https://logs-prod-<region>.grafana.net/loki/api/v1/push
GRAFANA_LOKI_USER=<logs-instance-id>
GRAFANA_PROM_REMOTE_WRITE_URL=https://prometheus-prod-<region>.grafana.net/api/prom/push
GRAFANA_PROM_USER=<metrics-instance-id>
GRAFANA_OTLP_TRACES_ENDPOINT=https://otlp-gateway-prod-<region>.grafana.net/otlp/v1/traces
GRAFANA_TEMPO_OTLP_GRPC_ENDPOINT=tempo-prod-<region>.grafana.net:443
GRAFANA_TEMPO_USER=<traces-instance-id>
```

값은 Grafana Cloud Portal의 stack 정보와 각 데이터소스 상세 화면에서 가져옵니다. region은 별도 입력값으로 외우지 않고, Cloud Portal이 보여 주는 endpoint URL에 포함된 값을 그대로 사용합니다. 수강생은 먼저 stack의 Instance Details에서 Grafana URL을 확인하고, 그 아래 Logs, Metrics, Tempo 각각의 파란 안내 박스에서 URL과 User를 복사합니다.

| 환경 변수 | Grafana Cloud에서 확인할 위치 | 입력 방식 |
| --- | --- | --- |
| `GRAFANA_CLOUD_URL` | Cloud Portal의 해당 stack 상세 화면에서 Grafana URL | `https://<stack>.grafana.net` 형태 |
| `GRAFANA_TELEMETRY_TOKEN` | Cloud Access Policy에서 `logs:write`, `metrics:write`, `traces:write` scope로 생성한 token | Alloy가 Logs/Metrics/Traces 전송에 공통 사용 |
| `GRAFANA_DASHBOARD_TOKEN` | Grafana instance의 Service Account token | dashboard import API 인증에 사용 |
| `GRAFANA_DASHBOARD_NAMESPACE` | 별도 변경이 없으면 기본값 사용 | `default` |
| `GRAFANA_DASHBOARD_UID` | 단일 dashboard JSON을 수동 import할 때만 사용 | 기본 두 dashboard import에서는 비워 둠 |
| `GRAFANA_FOLDER_UID` | import 대상 folder uid | 기본값 `ai-quality` |
| `GRAFANA_FOLDER_TITLE` | import 대상 folder 표시 이름 | 기본값 `AI Quality` |
| `GRAFANA_LOKI_URL` | Cloud Portal의 stack에서 Logs 또는 Loki 상세 정보 | Loki endpoint URL, `/loki/api/v1/push`는 스크립트가 붙임 |
| `GRAFANA_LOKI_PUSH_URL` | Logs 또는 Loki 상세 정보의 Alloy 예시 | `/loki/api/v1/push`까지 포함된 URL |
| `GRAFANA_LOKI_USER` | Logs 또는 Loki 상세 정보의 user/username/instance ID | 숫자 또는 문자열 그대로 입력 |
| `GRAFANA_PROM_REMOTE_WRITE_URL` | Cloud Portal의 Prometheus 또는 Metrics 상세 정보 | `/api/prom/push`가 포함된 remote_write URL |
| `GRAFANA_PROM_USER` | Prometheus 또는 Metrics 상세 정보의 username/instance ID | 숫자 또는 문자열 그대로 입력 |
| `GRAFANA_OTLP_TRACES_ENDPOINT` | Cloud Portal의 Tempo 또는 Traces 상세 정보 | 직접 OTLP/HTTP 확인이 필요할 때 참고 |
| `GRAFANA_TEMPO_OTLP_GRPC_ENDPOINT` | Tempo 상세 정보의 Alloy exporter 예시 | `tempo-prod-...grafana.net:443` 형태 |
| `GRAFANA_TEMPO_USER` | Tempo 또는 Traces 상세 정보의 user/username/instance ID | 숫자 또는 문자열 그대로 입력 |
| `GRAFANA_LABEL_SERVICE` | 실습 로그와 메트릭을 묶는 label | 기본값 `ai-quality-serving` |
| `GRAFANA_LABEL_ENVIRONMENT` | 실습 환경 label | 기본값 `training` |

Cloud Portal 화면에서는 비슷한 숫자가 여러 개 보이므로, 어떤 숫자를 어떤 키에 넣는지 분리해서 봐야 합니다. stack 상단의 `Instance ID`는 Grafana instance 자체의 식별자이고, Logs/Metrics/Tempo 전송 인증의 username으로 쓰는 값은 각 데이터소스 안내 박스의 `User`입니다.

| Cloud Portal 화면 | 화면에서 복사할 값 | `.env` 키 | 주의할 점 |
| --- | --- | --- | --- |
| Instance Details | `Url` | `GRAFANA_CLOUD_URL` | Dashboard API 호출에 사용 |
| Instance Details | `Instance ID` | 이번 Demo에서는 직접 사용하지 않음 | Logs/Metrics/Tempo의 `User`와 혼동하지 않음 |
| Logs 안내 박스 | `URL` | `GRAFANA_LOKI_URL` | 스크립트가 `/loki/api/v1/push`를 자동으로 붙임 |
| Logs Alloy 예시 | `/loki/api/v1/push` 포함 URL | `GRAFANA_LOKI_PUSH_URL` | Alloy config에서 그대로 사용 |
| Logs 안내 박스 | `User` | `GRAFANA_LOKI_USER` | Logs 전송 Basic Auth username |
| Access Policy token | `logs:write`, `metrics:write`, `traces:write` scope로 생성한 token | `GRAFANA_TELEMETRY_TOKEN` | Alloy 전송 공통 Basic Auth password |
| Metrics 안내 박스 | `URL` | `GRAFANA_PROM_REMOTE_WRITE_URL` | `/api/prom/push`까지 포함된 remote_write URL이어야 함 |
| Metrics 안내 박스 | `User` | `GRAFANA_PROM_USER` | Metrics remote_write Basic Auth username |
| Tempo 안내 박스 | `User` | `GRAFANA_TEMPO_USER` | Traces 전송 Basic Auth username |
| Tempo 또는 Traces ingest 안내 | OTLP traces endpoint | `GRAFANA_OTLP_TRACES_ENDPOINT` | 직접 OTLP/HTTP 확인이 필요할 때만 참고 |
| Tempo Alloy 예시 | `tempo-prod-...grafana.net:443` endpoint | `GRAFANA_TEMPO_OTLP_GRPC_ENDPOINT` | Alloy의 `otelcol.exporter.otlp`에서 사용 |

Dashboard token은 Grafana Cloud Portal의 stack card가 아니라 Launch로 들어간 Grafana instance 안에서 만듭니다. [Grafana Service accounts 문서](https://grafana.com/docs/grafana/latest/administration/service-accounts/)는 service account token을 Grafana HTTP API 인증에 쓰는 값으로 설명합니다. 이 token은 Grafana HTTP API가 dashboard를 생성하거나 갱신할 때 쓰는 인증값이므로, Logs/Metrics/Traces 전송에 쓰는 `GRAFANA_TELEMETRY_TOKEN`과 분리합니다.

| 순서 | Grafana 화면에서 할 일 | `.env`에 반영할 값 |
| --- | --- | --- |
| 1 | Cloud Portal에서 대상 stack의 `Launch` 클릭 | Grafana instance로 이동 |
| 2 | 왼쪽 메뉴에서 `Administration` 클릭 | 관리 화면 진입 |
| 3 | `Users and access` > `Service accounts` 클릭 | service account 목록 확인 |
| 4 | `Add service account` 클릭 후 이름 입력 | 예: `ai-quality-dashboard-import` |
| 5 | role을 `Editor`로 지정 | dashboard 생성/갱신 권한 확보 |
| 6 | 생성한 service account를 열고 `Add service account token` 클릭 | token 생성 화면 진입 |
| 7 | token 이름과 필요한 만료일을 입력하고 `Generate token` 클릭 | 표시된 token 값을 `GRAFANA_DASHBOARD_TOKEN`에 입력 |

Service account token은 생성 후 한 번만 복사할 수 있다고 가정하고 바로 안전한 secret 저장소나 개인 `.env`에 옮깁니다. 수업 demo에서는 dashboard import만 필요하므로 service account 이름과 token 이름에 `dashboard-import`처럼 용도를 드러내면 나중에 회수하거나 교체하기 쉽습니다. `Viewer` 권한은 dashboard import에 부족할 수 있으므로, 실습에서는 `Editor` role을 기준으로 안내합니다.

예를 들어 Cloud Portal에 `https://logs-prod-011.grafana.net`, `User 363390`이 보이면 `GRAFANA_LOKI_URL=https://logs-prod-011.grafana.net`, `GRAFANA_LOKI_PUSH_URL=https://logs-prod-011.grafana.net/loki/api/v1/push`, `GRAFANA_LOKI_USER=363390`처럼 입력합니다. Metrics 화면의 URL이 `/api/prom`까지만 보이는 경우에는 remote_write용으로 `/api/prom/push`까지 포함되는지 확인합니다. Tempo 화면의 datasource URL이 `https://tempo-prod-.../tempo` 형태로 보이더라도, Alloy exporter 예시는 `tempo-prod-...grafana.net:443` 형태의 gRPC endpoint를 사용합니다.

Grafana 공식 문서 기준으로 Metrics의 remote_write URL과 username은 Cloud Portal의 Prometheus card에서 Details를 열어 확인합니다. Traces 문서는 OpenTelemetry connection tile에서 `OTEL_EXPORTER_OTLP_ENDPOINT`와 `OTEL_EXPORTER_OTLP_HEADERS`를 생성해 쓰는 흐름을 안내하고, Tempo Alloy 예시는 `otelcol.exporter.otlp`와 `otelcol.auth.basic`을 사용합니다. 이 Demo에서 검증한 기본 경로는 Logs, Metrics, Traces write scope를 가진 `GRAFANA_TELEMETRY_TOKEN` 하나를 Alloy의 세 exporter가 공통으로 쓰는 방식입니다. Service account token은 Grafana HTTP API 자동화에 쓰는 값이며, 이 Demo에서는 `GRAFANA_DASHBOARD_TOKEN`에만 넣습니다.

Dashboard import는 `GRAFANA_DASHBOARD_TOKEN`으로 Grafana Dashboard API를 호출합니다. 실제 전송 전에 `--dry-run`으로 endpoint, folder uid, panel 수를 확인합니다. 스크립트는 먼저 `AI Quality` folder를 만들거나 재사용한 뒤 두 dashboard를 그 아래에 넣습니다. `GRAFANA_FOLDER_UID`와 `GRAFANA_FOLDER_TITLE`을 비워 두지 않으면 기본값은 각각 `ai-quality`, `AI Quality`입니다. 스크립트는 먼저 `dashboard.grafana.app` API와 `folder.grafana.app` API를 시도하고, stack에서 namespace 오류가 나면 기존 `/api/dashboards/db`, `/api/folders` API로 자동 전환합니다.

```bash
uv run python demos/ch04_grafana_cloud/02_import_dashboard.py --dry-run
uv run python demos/ch04_grafana_cloud/02_import_dashboard.py
```

Import된 dashboard는 Grafana의 `Dashboards` 메뉴에서 `AI Quality` folder 아래에 보입니다. folder 안에는 `AI Quality Overview`와 `AI Quality Details` 두 개가 있습니다. `AI Quality Overview`에는 요청 수, 오류 수, 지연 시간, `high_risk` 비율, `Service Reliability Trend`, `Score and Prediction Trend`, `Prediction Distribution`, `Score Bucket Distribution`, `Input Drift Delta Trend`, `Heart Rate Distribution: Reference vs Current`, `Oxygen Saturation Distribution: Reference vs Current` 패널이 들어갑니다. `AI Quality Details`에는 `Validation Failures`, `Model and Threshold Evidence`, `Input Error Evidence`, `Trace Search by course_trace_id`, `Correlated Logs by trace_id`, `Representative Request Trace`, `Service Topology Map`, `Service Graph Connectivity`, `Service Graph Latency p90` 패널이 들어갑니다. Grafana Cloud에서 datasource 이름이 다르게 보이면 dashboard 상단의 `metrics_datasource`, `logs_datasource`, `traces_datasource` 변수를 실제 Cloud datasource로 바꿉니다. `course_trace_id` 변수의 기본값은 `current-trace-0000`이며, trace sample을 보낸 뒤 같은 값으로 Loki 로그와 Tempo trace를 함께 확인합니다.

분포 패널은 평균만으로는 보이지 않는 변화를 확인하기 위한 보조 화면입니다. `ai_quality_prediction_count`는 `high_risk`, `low_risk` class별 건수를 보여 주고, `ai_quality_score_bucket_count`는 score bucket별 건수를 보여 줍니다. `ai_quality_input_histogram_count`는 기준선과 현재 입력의 feature bucket을 나란히 비교해 drift 후보를 확인합니다. 이 demo metric은 교육용 batch snapshot이므로, 실무 운영에서는 Prometheus histogram bucket과 quantile 설계를 별도로 검토해야 합니다.

Topology map은 trace 전송만으로 자동 표시되지 않습니다. Grafana Tempo의 service graph는 trace에서 생성된 `traces_service_graph_*` metric을 사용하고, Grafana Node Graph는 node/edge 형태의 데이터가 필요합니다. 이 Demo의 Alloy 설정은 `otelcol.connector.servicegraph`를 사용해 `qa-client -> ai-quality-serving -> input-validator/model-runtime/observability-pipeline` 호출 관계를 service graph metric으로 변환합니다. Details dashboard에서는 `Service Topology Map`으로 호출 관계를 먼저 보고, `Service Graph Connectivity`로 edge metric 생성 여부를 확인합니다.

Grafana Cloud로 Logs, Metrics, Traces를 보내는 기본 선택 경로는 Alloy container입니다. [Grafana Alloy Docker 문서](https://grafana.com/docs/alloy/latest/set-up/install/docker/)는 config file을 container에 mount하고 `grafana/alloy` image를 실행하는 방식을 안내합니다. 이 Demo의 `alloy.cloud.example.alloy`는 `loki.source.file`, `prometheus.scrape`, `otelcol.receiver.otlp`로 로컬 산출물을 읽고, `loki.write`, `prometheus.remote_write`, `otelcol.exporter.otlp`로 Grafana Cloud에 전송합니다.

```bash
uv run python demos/ch04_grafana_cloud/03_serve_metrics.py
docker compose -f demos/ch04_grafana_cloud/docker-compose.alloy.yml up
```

`03_serve_metrics.py`는 계속 실행되어 있어야 합니다. 다른 터미널에서 Alloy container를 띄우면 Alloy가 `artifacts/logs/chapter_04_anomaly_events.jsonl`을 Loki로 보내고, `http://host.docker.internal:9108/metrics`를 scrape해 Metrics로 보냅니다. Alloy UI는 `http://localhost:12345`에서 열어 component health와 전송 오류를 확인할 수 있습니다.

Alloy가 실행 중인 상태에서 trace sample을 local Alloy receiver로 보냅니다. 이 명령은 Grafana Cloud로 직접 인증하지 않고 `http://127.0.0.1:4318/v1/traces`에 OTLP/HTTP payload를 넣습니다. Cloud 인증과 전송은 Alloy가 담당합니다. 로그와 메트릭은 별도 push script를 쓰지 않습니다. 로그는 Alloy가 JSONL 파일을 읽고, 메트릭은 Alloy가 `03_serve_metrics.py`의 `/metrics` endpoint를 scrape합니다.

```bash
uv run python demos/ch04_grafana_cloud/04_send_traces_to_alloy.py
```

기본 trace sample은 30개 요청입니다. 각 요청은 `qa-client`의 client span, `ai-quality-serving`의 server span, 그리고 `input-validator`, `model-runtime`, `observability-pipeline`으로 이어지는 client/server span 쌍을 포함합니다. 요청 하나는 총 8개 span으로 구성되므로 기본 실행에서 240개 span을 보냅니다. 실행 출력의 `course_trace_id`, `tempo_trace_id`, `traceql`은 Details dashboard 변수에 그대로 넣어 확인할 수 있습니다.

운영처럼 데이터가 계속 들어오는 화면을 보고 싶으면 streaming sender를 사용합니다. 이 sender는 실행 중 매 batch마다 `data/operational_current_stream_events.jsonl`을 다시 읽고, 그 event를 현재 시각의 새 요청으로 바꿔 Alloy가 tailing하는 JSONL 로그 파일에 append합니다. 동시에 `03_serve_metrics.py`가 제공하는 Prometheus text 파일을 갱신하고, 같은 batch의 trace를 Alloy OTLP receiver로 보냅니다. 수업 중에는 `--max-batches`로 짧게 실행하고, 자유 실습에서는 값을 생략해 Ctrl-C 전까지 계속 보낼 수 있습니다.

```bash
uv run python demos/ch04_grafana_cloud/05_stream_observability_to_alloy.py --max-batches 10
```

기본 source event 파일은 2,000건입니다. `data/operational_current_events.jsonl` 120건은 문서와 보고서 예시의 수치를 고정하기 위한 current incident sample이고, `data/operational_current_stream_events.jsonl`은 Grafana dashboard를 운영처럼 보이게 하기 위한 streaming source입니다. Streaming sender는 이 source를 template처럼 사용해 새로운 `request_id`, `trace_id`, timestamp를 계속 만들기 때문에 dashboard에서는 요청 수와 검증 실패 수가 계속 증가합니다. 더 큰 JSONL source를 준비했다면 `--source-event-file`로 지정할 수 있습니다.

Streaming 출력에는 batch마다 대표 trace가 표시됩니다. 예를 들어 `course_trace_id=stream-trace-000000`이 나오면 Details dashboard의 `course_trace_id` 변수에 `stream-trace-000000`을 넣고, 같은 줄의 `tempo_trace_id`를 `tempo_trace_id` 변수에 넣습니다. 그러면 `Trace Search by course_trace_id`, `Correlated Logs by trace_id`, `Representative Request Trace`를 같은 요청 기준으로 확인할 수 있습니다.

Cloud Explore에서는 다음 LogQL, PromQL, TraceQL을 확인합니다.

```logql
{service="ai-quality-serving", environment="training"} | json | validation_failure="true"
```

```promql
ai_quality_high_risk_rate{service="ai-quality-serving", environment="training"}
```

```promql
sum(traces_service_graph_request_server_seconds_count{}) by (client, server)
```

```traceql
{ .course_trace_id = "current-trace-0000" }
```

Dashboard의 `Trace Search by course_trace_id` 패널도 같은 TraceQL을 사용합니다. `Representative Request Trace` 패널은 같은 샘플의 실제 Tempo trace id를 사용해 waterfall을 표시합니다. `Service Topology Map`이나 `Service Graph Connectivity`가 비어 있으면 Alloy UI에서 `otelcol.connector.servicegraph`와 `prometheus.remote_write` 상태를 먼저 확인합니다. trace 패널이 비어 있으면 Grafana 시간 범위를 최근 1시간으로 맞추고, 그 다음 `04_send_traces_to_alloy.py`를 다시 실행합니다.

trace payload만 확인하고 싶을 때는 `--dry-run`을 사용합니다. 이 명령은 payload preview를 만들고 span 수와 TraceQL을 출력하지만, Alloy나 Grafana Cloud로 전송하지 않습니다.

```bash
uv run python demos/ch04_grafana_cloud/04_send_traces_to_alloy.py --dry-run
```

입력 구성 변화 후보는 drift metric으로 함께 전송됩니다. Cloud Explore에서 `ai_quality_input_mean_delta{feature="heart_rate"}`, `ai_quality_input_histogram_count{feature="heart_rate"}`, `ai_quality_high_risk_rate_delta`를 조회하면 5장 `drift_report.md`로 넘어가기 전의 운영 관측 신호를 확인할 수 있습니다.

Grafana Cloud import를 실행하지 않은 경우 보고서에는 “Cloud 렌더링 미확인, 로컬 dashboard JSON과 payload preview 기준으로 확인”이라고 적습니다. 이 표현은 실패가 아니라 credential-gated Demo의 정상 fallback입니다.

## 실패 시 확인 포인트

Cloud 연결 실패는 “데이터가 없다”와 “인증 또는 endpoint가 맞지 않는다”를 분리해서 봐야 합니다. 실행 결과에 아래 메시지가 나오면 수강생은 먼저 token 종류와 endpoint 종류를 확인합니다.

| 실패 메시지 | 가능성이 높은 원인 | 조치 |
| --- | --- | --- |
| Dashboard import `Invalid API key` | `GRAFANA_TELEMETRY_TOKEN`을 Grafana dashboard API에 사용 | Grafana Service Account token을 만들어 `GRAFANA_DASHBOARD_TOKEN`에 입력 |
| Dashboard import `invalid namespace` | stack에서 `dashboard.grafana.app` namespace API가 맞지 않음 | 스크립트의 legacy API fallback 결과 확인 |
| Folder 생성 `Access denied` | service account가 folder/dashboard 생성 권한을 갖지 않음 | `GRAFANA_DASHBOARD_TOKEN`을 만든 service account role과 권한 확인 |
| Logs/Metrics/Traces가 모두 `invalid token`으로 실패 | access policy token 값이 아니거나 따옴표/공백까지 token으로 전달됨 | `GRAFANA_TELEMETRY_TOKEN` 값을 다시 복사하고 `.env` loader가 따옴표를 제거하는지 확인 |
| Alloy UI에서 `loki.write`, `prometheus.remote_write`, `otelcol.exporter.otlp`가 unhealthy | endpoint, user, `GRAFANA_TELEMETRY_TOKEN` 중 하나가 맞지 않음 | `.env`의 URL/User와 access policy scope를 Cloud Portal 안내와 대조 |
| Alloy trace export `invalid token` | `GRAFANA_TELEMETRY_TOKEN`이 Traces write 권한을 갖지 않음 | access policy scope와 `otelcol.exporter.otlp` 상태 확인 |
| Service Topology Map 또는 Service Graph Connectivity가 비어 있음 | service graph connector가 metric을 만들지 못했거나 remote_write가 실패함 | Alloy `otelcol.connector.servicegraph`, `otelcol.exporter.prometheus`, `prometheus.remote_write` 상태와 PromQL `traces_service_graph_request_server_seconds_count` 확인 |
| local Alloy trace 전송 실패 | Alloy OTLP receiver가 떠 있지 않거나 port가 다름 | `http://127.0.0.1:4318/v1/traces` receiver와 container port 확인 |
| Trace dashboard panel이 비어 있음 | trace sample을 보낸 시각과 dashboard 시간 범위가 맞지 않거나 Tempo 전송이 실패함 | 최근 1시간 범위에서 `04_send_traces_to_alloy.py` 재실행 후 Alloy `otelcol.exporter.otlp` 상태 확인 |
| Metrics가 Cloud에 보이지 않음 | `03_serve_metrics.py`가 실행 중이 아니거나 Alloy scrape가 실패함 | 로컬 `/metrics`, Alloy `prometheus.scrape`, `prometheus.remote_write` 상태 확인 |
| Logs가 Cloud에 보이지 않음 | 시간 범위, label, token, Loki endpoint 중 하나가 맞지 않음 | 현재 시간 범위와 `{service="ai-quality-serving", environment="training"}` LogQL 확인 |

## 보안 주의

Grafana Cloud API token, instance ID, username은 저장소에 기록하지 않습니다. 개인 실행 환경에서는 환경 변수 또는 개인 secret manager를 사용합니다. `GRAFANA_TELEMETRY_TOKEN` 하나로 Logs/Metrics/Traces write가 가능하므로 노출 영향이 큽니다. 실수로 토큰을 commit했거나 화면에 노출했다면 해당 token을 즉시 revoke하고 새 token으로 교체합니다.
