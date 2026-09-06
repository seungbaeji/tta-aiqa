# 5장 배포 판단

이 장은 9단계 여정의 **판단/rollback**과 **회고** 단계입니다. 관측 수집 묶음은
팀이 공유하고 개인 분석과 최종 판단은 개인이 작성합니다. 실제 overlay 전환과
rollback Demo는 강사와 플랫폼 범위입니다.

## 1. 판단/rollback

개인 분석의 입력 분포는 준비된 운영 표본에서 원인 후보를 좁히는 활동입니다.
새 모델 성능이나 대상 환경 상태를 확정하지 않습니다.

```bash
uv run jupyter nbconvert --to notebook --execute \
  labs/ch05-release-decision/00_compare_input_distributions.ipynb \
  --output /tmp/ch05-input-distribution.ipynb \
  --ExecutePreprocessor.timeout=120
```

### 1-1. Candidate B 모델 APPROVE와 운영 환경 확인 상태를 한 기록에서 분리한다

관측 수집 묶음은 live collection manifest
`artifacts/traffic/collection-session.json` 또는
`docs/reference/evidence/incident/prepared-observability-correlation.json`의
offline fixture입니다. Candidate B `APPROVE`는 공식 모델 판단으로 기록하되,
대상 `/v1/model`, GitOps sync와 운영 telemetry가 없으면
`operational_deployment_scope=target_pending`을 유지합니다.
대상 `/v1/model`의 프로필, 버전, 임계값은 runtime model identity 증거이고,
배포 선언의 예상 model SHA-256은 선언된 bundle identity 증거입니다. 두 증거를
하나로 합치지 않고 각각 대조해, 모델 승인과 대상 배포 확인을 분리합니다.
`local_verified`는 Candidate B를 실제 로컬에서 서빙하고 같은 모델의 요청과
운영 자료까지 확인했을 때만 사용할 수 있습니다. baseline local probe만
확인한 경우에는 `local_verified`로 기록하지 않습니다.

### 1-2. rollback trigger와 baseline 복구 완료를 선언할 evidence가 있는지 판단한다

`deploy/kubernetes/overlays/rollback/`은 기준 모델로 돌아갈 설정을 선언할 뿐
복구 완료를 증명하지 않습니다. 대상 model metadata, health, 같은 모델의 운영
신호와 강사 smoke 결과가 모두 확인되어야 실제 복구를 말할 수 있습니다.
의도한 invalid 422와 credential 누락은 자동 rollback 조건이 아닙니다.

수강생은 다음 정적 검사와 제공된 결과만 사용하며, cluster sync나 rollback 명령을
실행하지 않습니다.

```bash
uv run python scripts/run_model.py status --revision v2
uv run pytest -q \
  tests/integration/qa/test_v2_serialized_bundle_verification.py \
  tests/integration/deployment/test_kubernetes_contract.py
```

### 1-3. 현재 운영 권고가 모델 승인과 분리되는지 기록한다

개인 작업본을 열어 근거 목록과 교시별 기록을 연결합니다.

```bash
mkdir -p artifacts/reports
test -f artifacts/reports/release-decision-record.md || \
  cp labs/release-decision-record.md \
    artifacts/reports/release-decision-record.md
```

모델 승인, operational scope와 현재 권고를 별도 항목으로 씁니다. 대상 근거가
없으면 operational scope=`target_pending`으로 남깁니다. 실행하지 않은 경로의
evidence scope는 `offline`으로 기록하고, 실행 자체가 막힌 경우에는 별도
execution result=`BLOCKED`와 사유, 담당자를 남깁니다. local 200을 대상 승인으로
바꾸지 않습니다.

## 2. 회고

실행하지 않은 LIVE나 Agent 보고를 완료 근거로 쓰지 않습니다.

### 2-1. 판단 기록에서 판단 변화와 미확인 위험 인계를 복원한다

`release-decision-record.md`의 1일차 1부터 2일차 7까지 예상→관측→수정을 읽고
판단이 바뀐 이유를 복원합니다. 미확인 위험마다 운영 scope
(`target_pending` 또는 확인된 `target`/`local`), evidence scope (`static`/`offline`),
그리고 실행이 막힌 경우의 별도 execution result (`result=BLOCKED`, 사유, 담당자)를
각각 기록하고 필요한 자료와 재평가 조건을 남깁니다. 실행하지 않은 LIVE나 Agent
보고를 완료 근거로 쓰지 않습니다.

최종 기록에는 수집 묶음 ID, 개인 분석, 대표 요청/trace ID, 근거 목록과
내일 넘길 항목을 연결합니다. 요청 연결 기록과 팀 인계를 보존한 뒤 본인이 시작했고
다른 사람이 사용하지 않는 Compose만 정리합니다.

```bash
docker compose \
  -f deploy/compose/simple-mlops/compose.yaml \
  -f deploy/compose/simple-mlops/compose.grafana-cloud.yaml \
  down
```
