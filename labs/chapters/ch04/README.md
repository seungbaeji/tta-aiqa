# 4장 운영 상태 확인

이 장은 9단계 여정의 **관측**과 **traffic** 단계입니다. 관측 조건을 먼저
고정하고 관측 수집, 개인 분석으로 이어갑니다. LIVE는 강사가 Alloy
secret과 대시보드를 준비했다고 확인한 경우에만 선택합니다.

## 1. 관측

요청을 보내기 전에 확인 경로와 신호 기록 방식을 고정합니다. 아직
생성하지 않은 traffic의 결과를 관찰했다고 쓰지 않습니다.

### 1-1. LIVE/PREPARED 경로와 세 신호의 상관 조건을 실행 전에 정한다

요청을 보내기 전에 LIVE 또는 PREPARED/OFFLINE 경로를 하나 선택합니다.
강사가 Compose와 Grafana dashboard URL을 확인하지 않았다면 PREPARED/OFFLINE을
사용합니다. environment, model, UTC window와 run/request/trace correlation
조건을 먼저 기록하며, 아직 생성하지 않은 traffic의 결과를 관찰했다고 쓰지
않습니다.

### 1-2. 세 신호의 확인 범위와 상태를 traffic 실행 전에 기록 방식으로 고정한다

수집 뒤 collection manifest에 기록할 `not_checked`, `unavailable`, `available`
상태와 담당자를 실행 전에 정합니다. LIVE가 아니면
`docs/evidence/incident/prepared-observability-correlation.json`을
`scope=static` reference fixture로 읽고, 미실행 경로는 `offline`으로 둡니다.
secret과 token은 기록하지 않습니다. LIVE/PREPARED 선택이나 신호 확인이 막히면
환경 복구를 수강생 범위로 넓히지 않고 `result=BLOCKED`와 사유, 담당자를 수집
기록에 남깁니다.

## 2. traffic

관측 수집이 끝나도 개인 분석과 요청 연결 확인이 끝날 때까지 Compose를 내리지 않습니다.

### 2-1. baseline/current-shift/invalid traffic의 의도와 상태 코드를 인계한다

수집 팀은 실행, 기록, 완전성 확인 역할을 나눕니다. LIVE 경로에서는 다음 명령으로
세 시나리오를 한 번씩 실행하며 `--fast`를 사용하지 않습니다.

```bash
docker compose \
  -f deploy/compose.yaml \
  -f deploy/compose.grafana-cloud.yaml \
  up -d
docker compose \
  -f deploy/compose.yaml \
  -f deploy/compose.grafana-cloud.yaml \
  --profile traffic run --rm \
  --user "$(id -u):$(id -g)" \
  traffic-generator \
  course-session --scope local
```

생성 후 `artifacts/traffic/collection-session.json`과
`artifacts/traffic/compose.jsonl`에서 session ID, 환경, 모델, UTC, 세 run ID와
status code를 인계합니다. invalid의 422는 입력 검증 결과이며 5xx가 아닙니다.
LIVE가 없으면 `OBS-FALLBACK-02`를 `scope=static`으로 인계합니다.

LIVE 수집 뒤 signal 상태를 사람이 확인한 경우에만 매니페스트를 갱신합니다.
확인하지 않은 옵션은 명령에 넣지 않아 `not_checked`를 유지합니다.

```bash
docker compose \
  -f deploy/compose.yaml \
  -f deploy/compose.grafana-cloud.yaml \
  --profile traffic run --rm \
  --user "$(id -u):$(id -g)" \
  traffic-generator \
  course-session-status \
  --session-id '<course-session 출력의 session_id>' \
  --dashboard-url '<확인한 Grafana dashboard URL>' \
  --prometheus available \
  --loki available \
  --tempo available
```

PREPARED/OFFLINE 경로에서는 다음 reference fixture만 읽습니다.

```bash
uv run python -m json.tool \
  docs/evidence/incident/prepared-observability-correlation.json
```

관측 수집이 끝나도 개인 분석과 요청 연결 확인이 끝날 때까지 Compose를 내리지 않습니다.

### 2-2. 선택한 대표 요청이 지표, 로그, trace의 동일 사건으로 연결되는지 판정한다

개인 분석에서 수집 묶음의 normal/slow/invalid 중 하나를 골라 같은 run ID, request ID,
trace ID를 연결합니다. LIVE에서는 collection manifest와 JSONL을 사용합니다.

```bash
jq '{environment, scenarios: [.scenarios[] | {name, run_id}]}' \
  artifacts/traffic/collection-session.json
jq -c 'select(.run_id == "<RUN_ID>") |
  {scenario, run_id, request_id, status_code}' \
  artifacts/traffic/compose.jsonl
```

PREPARED/OFFLINE 경로에서는 대표 요청의 correlation과 trace path를 fixture에서
읽습니다.

```bash
jq '.representative_requests[] |
  {case, scenario, request_id: .correlation.request_id,
   run_id: .correlation.run_id, trace_id: .correlation.trace_id,
   log_event: .bounded_log_event.event,
   trace_path: [.trace_path[] |
     {span_name, span_kind, service_name, span_id, parent_span_id}]}' \
  docs/evidence/incident/prepared-observability-correlation.json
```

LIVE에서는 같은 두 식별자가 붙은 Risk API 로그와 trace를 조회합니다.

```logql
{service_name="risk-api", environment="<ENVIRONMENT>"} | json | run_id="<RUN_ID>" | request_id="<REQUEST_ID>"
```

```traceql
{ resource.service.name = "risk-api" && span."aiqa.run_id" = "<RUN_ID>" && span."aiqa.request_id" = "<REQUEST_ID>" }
```

Loki와 Tempo에서 같은 식별자를 찾을 때 request ID는 log/trace 연결에만 쓰고
Prometheus metric label에는 넣지 않습니다. PREPARED/OFFLINE에서는 fixture의
`representative_requests`와 `trace_path`를 읽되 실제 Loki/Tempo 검색으로 바꾸지
않습니다. 개인 분석 결과는 관측, 해석, 한계, 다음 확인 네 문장과 운영 관측 칸에 남깁니다.

## 3. 단계 완료

수집 인계 점검에서는 수집 묶음의 유형/ID와 environment, model, UTC 범위, 세 run ID,
신호 상태와 누락 사유를 공유합니다. 개인 분석에서는 같은 묶음의 범위를 복원하고
세 시나리오를 비교한 뒤 대표 요청을 선택해 log, metric, trace 연결을 분석하고,
그 결과를 운영 관측 칸에 인계합니다. 여기서 `result=BLOCKED`는 LIVE/PREPARED 선택이나
신호 확인 작업의 사유, 담당자를 나타내는 결과 필드입니다. 최종 운영 환경을
확인하지 못한 상태는 별도의 `operational scope=target_pending`으로 기록하며,
두 판단을 하나의 선택지로 합치지 않습니다.
