# 3장 서빙 환경 확인

이 장은 9단계 여정의 **API**와 **Kubernetes/GitOps** 단계입니다. 로컬 Compose
`http://127.0.0.1:8000`과 개인 공개 HTTPS(`AIQA_RISK_API_URL`)를 섞지
않습니다. 공개 주소는 가상 컴퓨터 이름에서 만들며 Proxmox 로그인 주소가
아닙니다. 대상 URL이 없으면 운영 scope를 `target_pending`으로 둡니다.

## 1. API

로컬 결과와 대상 결과를 섞지 않습니다. 이미지 빌드는 수강생 범위가 아닙니다.

### 1-1. Compose Risk API가 정상 입력과 의도한 422를 같은 계약으로 처리하는지 확인한다

강사가 준비한 이미지를 사용해 `risk-api`만 시작합니다. 이미지 빌드와 외부
노출은 수강생 범위가 아닙니다. `docker` 권한 오류, 이미지 없음, 모델 묶음 없음은
수강생이 고치지 않고 `API_NOT_RUNNING`과 `result=BLOCKED`로 기록합니다.

준비된 배포 선언을 먼저 읽습니다.

```bash
cat artifacts/models/revisions/v2/deployed/deployment.json
```

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml up -d --no-build risk-api
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/v1/model
uv run jupyter nbconvert --to notebook --execute \
  labs/ch03-serving/01_verify_risk_api.ipynb \
  --output /tmp/ch03-risk-api.ipynb \
  --ExecutePreprocessor.timeout=120
```

노트북은 정상 200과 의도한 422를 각각 한정 확인하는 bounded contract probe입니다.
실행된 `/tmp/ch03-risk-api.ipynb`에는 정상 응답의 `request_id`와
`X-Request-ID`, 의도한 422 결과가 남습니다. 실제 응답을 확인한 이 probe의
baseline scope는 `local`이며 Candidate B target 검증이 아닙니다. 이는 운영 관측
수집을 생성하는 단계가 아닙니다. API가 시작하지 않으면 없는 응답을 만들지 말고
`API_NOT_RUNNING`과 `result=BLOCKED`, 사유, 담당자를 기록합니다. 준비된 자료의
evidence scope는 `static` 또는 `offline`으로, 대상 운영 scope는
`target_pending`으로 각각 남깁니다. 세 시나리오 운영 수집은 관측 조건을 먼저
고정한 뒤 4장에서 `course-session`으로 실행합니다.

### 1-2. API model metadata와 bundle/deployment 선언이 같은 digest 의미를 갖는지 판단한다

`artifacts/models/revisions/v2/deployed/deployment.json`의 profile, version, 
SHA-256과 `/v1/model` 응답을 대조합니다. 이 API 단계에서는 운영 관측 수집 파일을
생성하지 않습니다. request ID와 `X-Request-ID`, 의도한 422는 실행된
`/tmp/ch03-risk-api.ipynb`의 bounded probe 결과에 남습니다. 이 대조는
`scope=local` 또는 `scope=static` 범위이며 대상 Candidate B 운영 완료가 아닙니다.

## 2. Kubernetes/GitOps

수강생은 제공된 결과의 범위, 시간, identity만 기록하고 cluster 명령을 수행하지
않습니다.

### 2-1. baseline, Candidate B, rollback overlay가 승인된 identity만 선택하는지 판단한다

overlay를 읽기 전에 선택될 모델 identity를 예측하고 다음 정적 계약 검사를
실행합니다.

```bash
uv run pytest -q tests/integration/deployment/test_kubernetes_contract.py \
  -k candidate_and_rollback_overlays_select_only_approved_models
```

Candidate A가 overlay에 없고 승인된 identity만 선택되는지 기록합니다. 정적
검사는 target sync PASS가 아닙니다.

### 2-2. Argo sync, KServe health, rollback 결과를 학습자 판단 범위와 분리한다

Argo Application 생성/sync, KServe health와 rollback은 강사 Demo입니다. 후보
동기화와 되돌리기는 강사와 플랫폼 책임입니다.
수강생은 제공된 결과의 범위, 시간, identity만 기록하고 cluster 명령을 수행하지
않습니다. 결과가 없으면 운영 scope는 `target_pending`으로 남기고, sync 실행이
막힌 경우에는 별도 execution result인 `result=BLOCKED`와 사유, 담당자를 기록합니다.
정적 overlay는 `scope=static`인 복구 의도이지 rollback 완료가 아닙니다.

## 3. 단계 완료

판단 기록의 서빙 확인 칸에 API 응답, model metadata, 정적 manifest와 실제 대상 환경에서 아직
확인하지 못한 범위를 나눠 기록합니다. 다음 **관측** 단계는 같은 model identity와
환경과 시간 범위를 기준으로 telemetry 조건을 먼저 정합니다.
