# 강의 D-1 실행 환경 점검

이 점검은 “파일이 맞다”는 정적 검사와 “실제 강의 환경에서 신호가
도착한다”는 실행 검사를 분리합니다. 실행 검사를 하지 못했다면 정적 검사
통과를 Grafana·Kubernetes 성공으로 기록하지 않습니다.

## 1. 정적 점검

두 저장소의 변경을 커밋한 뒤 실행합니다.

```bash
uv run python scripts/course_preflight.py \
  --scope static \
  --curriculum-repo ../ttamlops-2607
```

개발 중 연결만 확인할 때는 `--allow-dirty`를 사용할 수 있습니다. 이 옵션이
기록된 결과는 과정 발행 근거로 쓰지 않습니다.

정적 점검은 다음을 확인합니다.

- V2 모델 묶음·운영 데이터·준비된 사건 자료
- Docs v2·MkDocs 설정·V2 슬라이드 원본
- 두 Git 작업 공간의 미커밋 변경
- 최소 3 GiB의 남은 디스크 공간

결과는 기본적으로 `artifacts/reports/course-preflight.json`에 저장됩니다.

## 2. 비밀값과 로컬 노출 준비

Grafana Cloud를 사용하는 날에는 Alloy 비밀 파일 일곱 개를 준비하고,
소유자만 읽을 수 있게 합니다. 값 자체를 화면이나 점검 보고서에 출력하지
않습니다.

```bash
chmod 600 deploy/compose/simple-mlops/secrets/alloy/*
```

Dashboard API 토큰과 Alloy 전송 토큰은 분리합니다. 수업 종료 시각보다
지나치게 긴 수명을 주지 않고, 종료 뒤 회수할 담당자와 시각을 기록합니다.

Compose는 기본적으로 `127.0.0.1`에만 포트를 게시합니다.
`AIQA_COMPOSE_BIND_HOST=0.0.0.0`은 인증 없는 MLflow·Risk API·Alloy 관리
화면을 외부에 노출하므로, 방화벽과 접근 제어를 별도로 준비한 통제 환경
밖에서는 사용하지 않습니다.

## 3. 실제 환경 점검

서비스를 시작하기 전에 다음을 실행합니다.

```bash
uv run python scripts/course_preflight.py \
  --scope live \
  --curriculum-repo ../ttamlops-2607 \
  --expected-context "${TARGET_CONTEXT:?강사가 승인한 context가 필요합니다}" \
  --target-url "${TARGET_API_URL:?대상 API URL이 필요합니다}"
```

이 명령은 Docker daemon, Compose 설정, `5000`·`8000`·`12345` 포트,
비밀 파일의 존재·권한, Kubernetes context와 대상 readiness를 읽기 전용으로
확인합니다. `--scope live`에서는 `--expected-context`가 없거나 현재
context와 다르면 필수 검사 실패로 끝납니다. `--scope static`은 Kubernetes
context 없이 실행할 수 있습니다. 비밀값과 API 응답 본문은 보고서에
저장하지 않습니다.

점검을 통과하면 Grafana override를 포함해 서비스를 시작합니다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  up -d --build

curl --fail http://127.0.0.1:8000/health/ready
curl --fail http://127.0.0.1:8000/v1/model
```

## 4. 관측성 smoke test

각 실행에는 새로운 run ID를 사용합니다. Grafana의 수집 간격을 고려해
`labs/ch04-observability/README.md`에 적힌 일반 속도로 baseline과
`current-shift`를 보냅니다.

다음 항목이 같은 실행·시간대인지 확인합니다.

- 대시보드에서 `environment`, `model_profile`, `scenario`를 구분할 수 있음
- 422가 5xx 오류율과 분리되고 제한된 오류 분류만 로그에 남음
- 대표 request ID로 Loki 로그와 Tempo trace를 연결할 수 있음
- trace가 `traffic.generate`에서 Risk API SERVER span과
  `risk.predict`까지 이어짐
- 원본 특성값, 토큰, 긴 외부 correlation ID가 telemetry에 남지 않음

Cloud 수집이 15분 안에 확인되지 않으면 재시작을 반복하지 않습니다. 준비된
오프라인 사건 묶음으로 전환하고 실시간 수집은 `미확인`과 담당자·재점검
시각으로 남깁니다.

## 5. 종료와 회복 확인

수업 뒤에는 컨테이너와 네트워크를 정리하되, 감사에 필요한 실행 결과를
먼저 보존합니다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  down --remove-orphans
```

다음 항목은 자동 명령에 맡기지 않고 담당자가 완료 시각을 기록합니다.

- 단기 Grafana 토큰 회수 또는 회전
- 공동 대시보드와 실습 telemetry의 보존·삭제 기한
- Kubernetes 임시 Secret과 학생별 namespace 정리
- 롤백 뒤 모델 정보·대표 요청·새 관측 시간대 재확인

실패한 점검은 성공한 항목으로 덮지 않습니다. 새 점검 결과를 별도 파일로
남기고, 무엇을 고친 뒤 어떤 범위가 통과했는지 연결합니다.
