# 강의 시작 전 실행 환경 점검

이 점검 안내서는 강의 전에 서로 다른 세 범위를 따로 확인하기 위한 것입니다.
사전 점검(preflight) 결과는 파일·설정·연결의 **사전 구성** 근거입니다.
통과하더라도 실제 Grafana 신호 도착, Kubernetes 배포 완료, 대상 모델 일치까지
보증하지 않습니다.

## 1. 세 점검 범위

| scope | 확인할 질문 | 확인하지 않는 것 |
| --- | --- | --- |
| `static` | 두 저장소의 필수 파일, Git 상태와 디스크가 준비됐는가 | Docker, Grafana, Kubernetes, 대상 API |
| `compose-observability` | Compose 실행 전 포트·Docker·설정·비밀 파일·대시보드 설정·host artifact 쓰기가 준비됐는가 | 원격 지표·로그·추적 기록(trace) 도착, Kubernetes |
| `kubernetes-target` | 현재 연결 대상(context)이 승인된 값이며 대상 API 준비 상태(readiness)가 응답하는가 | Compose, GitOps 동기화, 모델 일치, 운영 신호 |

한 scope의 통과를 다른 scope의 성공으로 바꾸어 기록하지 않습니다. 결과 파일도
범위마다 나누어 보존합니다.

## 2. 정적 점검

두 저장소의 발행 대상 변경을 커밋한 뒤 실행합니다.

```bash
uv run python scripts/course_preflight.py \
  --scope static \
  --curriculum-repo ../ttamlops-2607 \
  --output artifacts/reports/course-preflight-static.json
```

다음을 확인합니다.

- V2 모델 묶음·운영 데이터·준비된 사건 자료
- Docs v2·MkDocs 설정·V2 슬라이드 원본
- 두 Git 작업 공간의 미커밋 변경
- 최소 3 GiB의 남은 디스크 공간

개발 중 연결만 확인할 때는 `--allow-dirty`를 사용할 수 있습니다. 이 옵션이
기록된 결과는 과정 발행 근거로 사용하지 않습니다.

## 3. Compose 관측성 준비

Grafana Cloud를 사용하는 날에는 Alloy 비밀 파일 일곱 개와
`.env.grafanacloud`를 준비합니다. 값 자체를 화면이나 점검 보고서에 출력하지
않고, 소유자만 읽을 수 있게 합니다.

```bash
test -f .env.grafanacloud || \
  cp .env.grafanacloud.example .env.grafanacloud
chmod 600 .env.grafanacloud
chmod 600 \
  deploy/compose/simple-mlops/secrets/alloy/metrics-url \
  deploy/compose/simple-mlops/secrets/alloy/metrics-username \
  deploy/compose/simple-mlops/secrets/alloy/logs-url \
  deploy/compose/simple-mlops/secrets/alloy/logs-username \
  deploy/compose/simple-mlops/secrets/alloy/otlp-url \
  deploy/compose/simple-mlops/secrets/alloy/otlp-username \
  deploy/compose/simple-mlops/secrets/alloy/api-key

uv run python scripts/course_preflight.py \
  --scope compose-observability \
  --curriculum-repo ../ttamlops-2607 \
  --output artifacts/reports/course-preflight-compose.json
```

이 범위는 Docker daemon, Compose 설정, `5000`·`8000`·`12345` 포트, Alloy 비밀
파일의 존재·권한, 대시보드 환경 파일의 필수 키·권한·HTTPS URL을 확인합니다.
또한 `artifacts/traffic`에서 고유한 임시 파일의 생성·쓰기·원자적 교체·삭제를
실제로 확인합니다. 기존 파일의 내용이나 권한은 읽거나 바꾸지 않고 임시 파일명과
내용도 보고서에 저장하지 않습니다.
설정이 올바르다는 뜻일 뿐, 실제 신호 도착을 보증하지 않습니다.

강의 시작 전에는 이미지 빌드와 대시보드 가져오기까지 마치고 트래픽은 보내지 않습니다.

```bash
uv run --package aiqa-grafana-dashboard-importer \
  aiqa-grafana-dashboard --check
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  build
uv run --package aiqa-grafana-dashboard-importer aiqa-grafana-dashboard
```

대시보드 API 토큰과 Alloy 전송 토큰은 분리합니다. 수업 종료 시각보다 지나치게
긴 수명을 주지 않고, 종료 뒤 회수할 담당자와 시각을 기록합니다.

Compose는 기본적으로 `127.0.0.1`에만 포트를 게시합니다.
`AIQA_COMPOSE_BIND_HOST=0.0.0.0`은 인증 없는 MLflow·Risk API·Alloy 관리 화면을
외부에 노출하므로 방화벽과 접근 제어를 준비한 통제 환경 밖에서는 사용하지
않습니다.

## 4. Kubernetes 대상 준비

강사가 승인한 연결 대상과 대상 API의 HTTP(S) 기본 URL(base URL)을 받은 경우에만
실행합니다. `--target-url`에는 `/health/ready`를 붙이지 않습니다. 스크립트가 이
경로를 한 번 추가합니다.

```bash
uv run python scripts/course_preflight.py \
  --scope kubernetes-target \
  --curriculum-repo ../ttamlops-2607 \
  --expected-context "${TARGET_CONTEXT:?강사가 승인한 context가 필요합니다}" \
  --target-url "${TARGET_API_URL:?대상 API base URL이 필요합니다}" \
  --output artifacts/reports/course-preflight-kubernetes.json
```

연결 대상이 다르거나 대상 URL이 없으면 필수 검사 실패로 끝납니다. 준비 상태의
HTTP 200은 해당 경로에 연결됐다는 근거일 뿐, GitOps 동기화·대상 모델 정보·정상
예측·Grafana 수집을 확인한 결과가 아닙니다.

플랫폼 담당자가 각 오버레이를 동기화한 뒤에는 별도의 읽기 전용 검증기를
실행합니다. live 기준 상태가 필요하면 `baseline` 대신 Alloy를 포함한
`baseline-observed` 오버레이를 동기화합니다. 검증기의 release 이름
`baseline`, `candidate-b`, `rollback`마다 출력 파일을 분리합니다.

```bash
uv run python scripts/verify_target_release.py \
  --expected-context "${TARGET_CONTEXT:?강사가 승인한 context가 필요합니다}" \
  --release candidate-b \
  --target-url "${TARGET_API_URL:?대상 API base URL이 필요합니다}" \
  --output artifacts/reports/target-candidate-b.json
```

이 명령은 리소스를 생성·수정·동기화하지 않습니다. 고정 이미지와 실제 Pod의
플랫폼 manifest digest, 모델 해시와 경로, 준비 상태, 모델 정보, 정상 요청을
확인합니다. 보고서의 `release_passed=true`는 해당 단계의 배포 확인 결과이며,
`live_telemetry_status=not_checked`는 Grafana 근거를 아직 별도로 확인해야 한다는
뜻입니다.

## 5. P5 수집과 인계

P5에는 강의 시작 전에 빌드한 서비스를 시작하고 표준 세션을 한 번 실행합니다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  up -d
curl --fail http://127.0.0.1:8000/health/ready
curl --fail http://127.0.0.1:8000/v1/model

docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  --profile traffic run --rm \
  --user "$(id -u):$(id -g)" \
  traffic-generator \
  course-session --scope local
```

`course-session`은 baseline, current-shift, invalid를 정해진 순서로 실행합니다.
출력의 `session_id`는 상태 갱신 명령에 그대로 전달합니다.
수집 매니페스트(collection manifest)
`artifacts/traffic/collection-session.json`과 응답 자료
`artifacts/traffic/compose.jsonl`을 P6에 인계합니다. 환경·모델·UTC 범위, 세
시나리오의 run ID·상태 코드와 빠진 신호를 함께 기록합니다.

생성 직후 `dashboard_url=null`이며 Prometheus·Loki·Tempo는 모두
`not_checked`입니다. 대시보드에서 같은 범위를 사람이 확인한 뒤 수집
매니페스트를 갱신합니다.

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

찾지 못한 신호는 `unavailable`로 바꾸고, 확인하지 않은 신호 옵션은 생략해
`not_checked`로 남깁니다. 이는 자동 탐지가 아니라 확인한 사람이 기록한
결과입니다. 상태 갱신은 새 트래픽을 보내지 않습니다.

두 `docker compose run` 명령의 `--user`는 결과 파일을 현재 host 사용자 소유로
남깁니다. root 실행이나 과도하게 넓은 디렉터리 권한으로 우회하지 않습니다.

P5가 끝나도 Compose를 내리지 않습니다. P6와 P7이 같은 시간 범위와 식별자를
사용해야 합니다.

## 6. P6 분석과 P7 대표 요청 추적

P6에는 같은 수집 묶음의 범위를 복원하고 세 시나리오를 비교한 뒤 대표 요청과
E-05를 남깁니다. P7에는 P6에서 고른 대표 요청의 run ID와 request ID로 Loki
로그와 Tempo 추적 기록을 연결합니다.
새 트래픽을 보내지 않습니다.

다음 항목이 같은 환경·모델·UTC 범위인지 확인합니다.

- 대시보드에서 `environment`, `model_profile`, `scenario`를 구분할 수 있음
- 422가 5xx 오류율과 분리되고 제한된 오류 분류만 로그에 남음
- 대표 request ID로 Loki 로그와 Tempo 추적 기록을 연결할 수 있음
- 추적 기록이 `traffic.generate`에서 Risk API 서버 구간(span)과
  `risk.predict`까지 이어짐
- 원본 특성값, 토큰, 긴 외부 correlation ID가 관측 기록(telemetry)에 남지 않음

실제 run ID와 request ID를 찾는 방법과 조회식은
`labs/ch04-observability/README.md`를 따릅니다. P5 인계 점검에서 live 필수
의미와 필요한 신호 상태를 확인하지 못하면 재시작을 반복하지 않습니다. 준비된
오프라인 수집 묶음으로 전환하고 실시간 수집은 `미확인`과 담당자·재점검 시각으로
남깁니다.

## 7. 종료와 회복 확인

P7 기록과 팀 인계 자료를 보존한 뒤, 본인이 시작했고 다른 사람이 사용하지 않는
Compose 작업만 정리합니다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  down --remove-orphans
```

다음 항목은 자동 명령에 맡기지 않고 담당자가 완료 시각을 기록합니다.

- 단기 Grafana 토큰 회수 또는 회전
- 공동 대시보드와 실습 관측 기록의 보존·삭제 기한
- Kubernetes 임시 Secret과 학생별 namespace 정리
- 롤백 뒤 모델 정보·대표 요청·새 관측 시간대 재확인

실패한 점검은 성공한 항목으로 덮지 않습니다. 새 점검 결과를 별도 파일로 남기고,
무엇을 고친 뒤 어떤 범위가 통과했는지 연결합니다.

## 8. 수강생 본편과 메모리

수강생 여정·SSH alias·API URL·GitOps 역할은
[실습 안내](../../labs/README.md)가 기준입니다. KServe 설치, GHCR credential,
Argo sync, WireGuard 복구는 이 점검 안내서와 플랫폼 작업이며 수강생 본편이
아닙니다.

약 4GiB VM에서는 단계별로 필요한 Compose 서비스만 켭니다. 한도는
[4GiB VM 메모리](../../labs/README.md#4gib-vm-메모리)를 따릅니다. 대상 API URL은
강사가 제공하고, 수강생이 ClusterIP port-forward를 만들도록 안내하지 않습니다.
