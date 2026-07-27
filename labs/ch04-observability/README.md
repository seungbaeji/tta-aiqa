# 4장 운영 상태 확인

## 1. 목표와 교시별 산출물

이 실습은 화면을 여는 데서 끝나지 않습니다. 같은 환경·모델·UTC 시간 범위에서
지표로 변화 구간을 찾고, 로그와 추적 기록으로 대표 요청을 좁혀 원인 후보와 한계를
기록합니다. 운영 요청에는 정답이 없으므로 새 재현율·정밀도·미탐 수를 계산하지
않습니다.

| 교시 | 작업 단위 | 끝날 때 남길 것 |
| --- | --- | --- |
| P5 · 팀 수집 | 실행 / 기록 / 완전성 확인 | 공유 수집 묶음 ID, 환경, 모델, UTC 범위, 시나리오별 run ID, 수집 누락 |
| P6 · 개인 분석 | 같은 수집 묶음을 각자 분석 | baseline/current-shift 비교, 대표 요청, 해석, 한계, 다음 확인 |
| P7 · 대표 요청 추적 | normal / slow / 422 가운데 요청을 연결 | request ID, trace ID, span 경로, 최종 권고에 미친 영향 |

실시간 환경이 없으면 준비된 정적 수집 묶음을 사용합니다. 정적 수집 묶음을 읽은 사실을
실제 Grafana 수집 성공이나 대상 환경 확인으로 바꾸어 쓰지 않습니다.

## 2. P5 시작 경로 선택

환경 구축은 강의 실습이 아닙니다. 강사 또는 환경 담당자는 강의 시작 전에
[실행 환경 점검 안내](../../docs/runbooks/course-preflight.md)에 따라 이미지,
Alloy 접속 정보와 대시보드를 준비합니다. 수강생은 비밀값을 만들거나 대시보드를
가져오거나 이미지를 빌드하지 않습니다.

P5를 시작할 때 다음 둘 중 하나만 고릅니다.

- **LIVE**: 강사가 Compose와 Grafana 대시보드가 준비됐다고 확인했고, 사용할
  대시보드 URL과 데이터 소스를 안내한 경우
- **PREPARED/OFFLINE**: 위 준비 상태 가운데 하나라도 확인되지 않은 경우

LIVE를 골라도 비밀값, 토큰, 원본 특성을 명령 출력이나 판단 기록에 복사하지
않습니다. 준비 여부가 모호하면 환경을 고치는 데 머물지 말고 정적 수집 묶음으로
진행합니다.

## 3. P5 · 팀 수집

팀은 역할을 먼저 정합니다.

- **실행**: Compose와 세 트래픽 시나리오를 한 번씩 실행합니다.
- **기록**: 모델 정보, UTC 시작·종료, run ID와 Grafana 조회 범위를 남깁니다.
- **완전성 확인**: baseline/current-shift/invalid와 상태 코드, 지표·로그·trace의
  누락을 확인합니다.

Docker, Alloy, Grafana Cloud 설정이 준비된 경우에만 실시간 경로를 실행합니다.
Alloy는 15초마다 수집하므로 이 실습에서는 `--fast`를 사용하지 않습니다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  up -d
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  --profile traffic run --rm \
  --user "$(id -u):$(id -g)" \
  traffic-generator \
  course-session --scope local
```

`course-session`은 baseline, current-shift, invalid를 정해진 순서로 실행합니다.
세션 ID는 실행할 때마다 자동으로 새로 생성됩니다. 명령 출력의 `session_id`는
다음 상태 갱신 명령에서 그대로 사용합니다.
호스트에는 다음 두 파일이 남습니다.

- **수집 매니페스트(collection manifest)**:
  `artifacts/traffic/collection-session.json`
- **시나리오별 응답 JSONL**: `artifacts/traffic/compose.jsonl`

생성 직후 수집 매니페스트의 `dashboard_url=null`이고, `prometheus`·`loki`·
`tempo`의 `signal_availability.status`는 모두 `not_checked`입니다. 이는 수집
실패가 아니라 아직 사람이 대시보드에서 확인하지 않았다는 뜻입니다.

대시보드의 같은 환경·모델·UTC 범위에서 신호를 확인한 뒤 결과를 명시적으로
갱신합니다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
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

각 신호를 찾지 못했다면 해당 `available`을 `unavailable`로 바꿉니다. 이 상태는
자동 탐지 결과가 아니라 대시보드를 본 사람의 확인 결과입니다. 확인하지 않은
옵션은 명령에서 빼며, 생략한 신호는 `not_checked` 상태를 유지합니다. 이 명령은
수집 매니페스트만 갱신하고 새 트래픽을 보내지 않습니다.

`--user "$(id -u):$(id -g)"`는 bind mount에 만든 파일을 현재 host 사용자 소유로
남깁니다. 이 옵션을 빼고 root 권한이나 과도하게 넓은 디렉터리 권한으로 우회하지
않습니다.

수집 매니페스트의 `session_id`, 환경, scope, 모델 정보, UTC 시작·종료, 세
시나리오의 run ID·상태 코드 구성·artifact path를 팀 수집 묶음으로 공유합니다.
`artifacts/traffic/compose.jsonl`과 대시보드에서 같은 run ID를 다시 찾을 수 있어야
P5 수집을 마칩니다. `invalid`의 422는 입력 검증 결과이며 5xx 서비스 오류가
아닙니다.

인계 점검에서 `live` 경로에 필요한 환경·모델·세 run ID·절대 UTC 범위와
신호 상태를 확인하지 못하면 재시작을 반복하지 않고 아래 정적 수집 묶음으로
전환합니다. 실시간 신호 상태는 `not_checked` 또는 `unavailable`과 확인한
사람·시각을 그대로 남깁니다.

!!! danger "P6와 P7까지 실행 상태를 보존합니다"
    **P5가 끝났다고 `docker compose down`을 실행하지 않습니다.** P6가 같은
    시간 범위를 분석하고 P7이 같은 request ID를 추적한 뒤에만 정리합니다.

### [PREPARED/OFFLINE] 정적 팀 수집 묶음

Grafana Cloud, Loki 또는 Tempo를 사용할 수 없으면 다음 파일 하나를 P5 팀 수집
묶음으로 고정합니다.

```bash
uv run python -m json.tool \
  docs/reference/evidence/incident/prepared-observability-correlation.json
```

이 파일은 실제 수집 자료가 아니라 `PREPARED/OFFLINE` 정적 fixture입니다.
`provenance`, `observation_window`, `environment`, `model`을 먼저 확인하고,
`dashboard.scenario_summaries`에 baseline/current-shift/invalid가 모두 있는지
검사합니다. `handoff_contract`는 실시간 경로의 수집 매니페스트
`artifacts/traffic/collection-session.json`과 응답 자료
`artifacts/traffic/compose.jsonl`에 대응하는 경로를 설명합니다. 원본 특성값과
secret은 포함하지 않습니다.

판단 기록의 P5 행에는 수집 묶음 ID `OBS-FALLBACK-02`, `scope=static`, 파일
경로와 실시간 수집을 확인하지 못한 이유를 남깁니다.

## 4. P6 · 개인 분석

P5 수집 묶음을 바꾸거나 새 트래픽을 보내지 않고 다음 완료 조건까지 분석합니다.

1. **범위 복원**: 수집 묶음 ID, 환경, 모델, UTC 범위와 분석 질문을 고정합니다.
2. **세 시나리오 비교**: baseline과 current-shift의 상태, 고위험 예측 비율, score P95,
   missing-features P95, latency P95를 비교합니다.
3. **대표 요청 선택**: normal·slow·422 대표 요청 가운데 지표 변화와 연결할 대상을
   고르고, 강화되거나 약화된 원인 후보를 적습니다.
4. **E-05 인계**: 정답 부재, 확인하지 못한 환경, 다음 담당자와 자료를 적습니다.

실시간 경로에서는 대시보드의 환경·Scenario·모델 범례와 UTC 시간 선택을
고정합니다. 오프라인 경로에서는 `dashboard.time_series`와
`representative_requests`를 사용합니다. 둘 다 같은 네 문장으로 끝냅니다.

- **관측**: 어느 범위에서 무엇이 달라졌는가
- **해석**: 어떤 원인 후보가 강화·약화됐는가
- **한계**: 이 자료만으로 무엇을 확정할 수 없는가
- **다음 확인**: 누가 어떤 자료를 확인하면 판단을 다시 여는가

P6 결과는 개인 작업본의 D2-P6 행과 E-05에 기록합니다. 팀 문장을 그대로
복사하지 않고, 같은 수집 묶음에서 자신이 선택한 비교와 한계를 씁니다.

## 5. P7 · 대표 요청 추적

P6에서 분석 대상으로 고른 요청을 그대로 추적합니다. 새 트래픽을 보내지
않습니다. **P5에서 정한 live/offline 경로 가운데 하나만** 따릅니다. 오프라인
수집 묶음을 골랐다면 live 파일, Loki, Tempo 명령을 실행하지 않습니다.

### [PREPARED/OFFLINE] 준비된 요청 연결

오프라인 수집 묶음의 `representative_requests`에는 `normal`, `slow`,
`invalid_422`가 같은 구조로 들어 있습니다. P6에서 고른 요청의 `correlation`,
`bounded_log_event`, `trace_path`를 따라갑니다. 준비된 식별자는 실제 Loki나
Tempo에서 검색하지 않고, 증거 범위는 `scope=static`으로 유지합니다.

```bash
jq '.representative_requests[] |
  {case, scenario, request_id: .correlation.request_id,
   run_id: .correlation.run_id, trace_id: .correlation.trace_id,
   log_event: .bounded_log_event.event,
   trace_path: [.trace_path[] |
     {span_name, span_kind, service_name, span_id, parent_span_id}]}' \
  docs/reference/evidence/incident/prepared-observability-correlation.json
```

### [LIVE] 저장한 요청 연결

수집 매니페스트에서 해당 시나리오의 실제 `<RUN_ID>`와 `<ENVIRONMENT>`를
확인하고, `artifacts/traffic/compose.jsonl`에서 같은 run ID의 응답 중 하나를 골라
`<REQUEST_ID>`를 확인합니다.

```bash
jq '{environment, scenarios: [.scenarios[] | {name, run_id}]}' \
  artifacts/traffic/collection-session.json
jq -c 'select(.run_id == "<RUN_ID>") |
  {scenario, run_id, request_id, status_code}' \
  artifacts/traffic/compose.jsonl
```

아래 자리표시자를 방금 확인한 값으로 바꿉니다. Loki에서 실행과 요청이 모두 같은
로그를 찾습니다.

```logql
{service_name="risk-api", environment="<ENVIRONMENT>"} | json | run_id="<RUN_ID>" | request_id="<REQUEST_ID>"
```

P6에서 고른 요청이 422일 때에만 제한된 오류 이벤트 조건을 추가합니다.

```logql
{service_name="risk-api", environment="<ENVIRONMENT>"} | json | run_id="<RUN_ID>" | request_id="<REQUEST_ID>" | event="model.input.validation.failed"
```

Tempo에서는 같은 두 식별자가 붙은 Risk API span을 찾습니다.

```traceql
{ resource.service.name = "risk-api" && span."aiqa.run_id" = "<RUN_ID>" && span."aiqa.request_id" = "<REQUEST_ID>" }
```

Compose에서는 `traffic.generate → risk-api.predict`(CLIENT) →
`POST /v1/predict`(SERVER) → `risk.predict` 순서와 같은 trace ID를 확인합니다.
정상 요청은 HTTP 200 경로, slow 요청은 P6에서 정한 지연 조건을 넘은 200 경로,
422는 `MODEL_INPUT_INVALID`와 제한된 `validation_category`가 있는 경로입니다.

## 6. 완료 기준과 정리

개인 기록에는 수집 묶음 ID, 환경, 모델, UTC 범위, 시나리오, 관측값, 대표
request ID·trace ID, 해석, 한계와 다음 담당자가 있어야 합니다. 실시간 확인이
실패했다면 관측 결과에 `result=BLOCKED`와 사유·담당자를 남깁니다. Candidate B의
대상 근거가 없다면 최종 운영 환경 확인 상태는 별도로 `target_pending`으로 둡니다.

P7 기록과 팀의 수집 인계를 보존한 뒤, 본인이 시작했고 다른 사람이 사용하지 않는
Compose 작업만 종료합니다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  down
```
