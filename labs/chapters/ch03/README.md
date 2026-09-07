# 3장 서빙 환경 확인

이 장은 9단계 여정의 **API**와 **Kubernetes/GitOps** 단계입니다. 로컬 Compose
`http://127.0.0.1:8000`과 개인 공개 HTTPS(`AIQA_RISK_API_URL`)를 섞지
않습니다. 공개 주소는 가상 컴퓨터 이름에서 만들며 Proxmox 로그인 주소가
아닙니다. 대상 URL이 없으면 운영 scope를 `target_pending`으로 두고 identity를
만들지 않습니다.

Application 생성, KServe 설치, GHCR pull secret은 플랫폼이 이미 준비합니다.
이미 등록된 Application을 `deploy/k8s/candidate-b`로 바꾸고
`${AIQA_RISK_API_URL}/v1/model`이 Candidate B digest인지 확인하는 것은 수강생
범위입니다.

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
docker compose -f deploy/compose.yaml up -d --no-build risk-api
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/v1/model
uv run jupyter nbconvert --to notebook --execute \
  labs/chapters/ch03/01_verify_risk_api.ipynb \
  --output /tmp/ch03-risk-api.ipynb \
  --ExecutePreprocessor.timeout=120
```

노트북은 정상 200과 의도한 422를 각각 한정 확인하는 bounded contract probe입니다.
실행된 `/tmp/ch03-risk-api.ipynb`에는 정상 응답의 `request_id`와
`X-Request-ID`, 의도한 422 결과가 남습니다. 이미지는 실행 환경, 컨테이너는
실행 중인 인스턴스, 모델 파일은 예측 규칙입니다. 200은 이 요청이 규약을
통과했다는 뜻이고, 422는 입력 규약 오류이며 모델 품질 오류가 아닙니다. 본문이
너무 크면 413, 서버 처리 문제는 5xx입니다. 요청 ID는 나중에 로그와 처리 경로에서
같은 요청을 찾는 연결값이며 인증 정보가 아닙니다. 실제 응답을 확인한 이 probe의
baseline scope는 `local`이며 Candidate B target 검증이 아닙니다. 이는 운영 관측
수집을 생성하는 단계가 아닙니다. API가 시작하지 않으면 없는 응답을 만들지 말고
`API_NOT_RUNNING`과 `result=BLOCKED`, 사유, 담당자를 기록합니다. 준비된 자료의
evidence scope는 `static` 또는 `offline`으로, 대상 운영 scope는
`target_pending`으로 각각 남깁니다. 세 시나리오 운영 수집은 관측 조건을 먼저
고정한 뒤 4장에서 `course-session`으로 실행합니다.

### 1-2. API model metadata와 bundle/deployment 선언이 같은 digest 의미를 갖는지 판단한다

`artifacts/models/revisions/v2/deployed/deployment.json`의 profile, version, 
SHA-256과 `/v1/model` 응답을 대조합니다. API 응답, 모델 묶음 정보, 배포 설정이
같은 식별값을 가리키는지 보고, 한 자료의 이름만으로 실행 모델을 확정하지
않습니다. `profile`, `version`, `threshold`, 특성 수, 해시 중 다른 항목이 있으면
그 항목이 가리키는 설정, 파일, 실행 상태를 추가로 확인하고 자동 복구 결론을
내지 않습니다. 로컬 성공은 대상 배포 성공을 대신하지 않습니다. 이 API 단계에서는
운영 관측 수집 파일을 생성하지 않습니다. request ID와 `X-Request-ID`, 의도한
422는 실행된 `/tmp/ch03-risk-api.ipynb`의 bounded probe 결과에 남습니다. 이
대조는 `scope=local` 또는 `scope=static` 범위이며 대상 Candidate B 운영 완료가
아닙니다.

## 2. Kubernetes/GitOps

로컬 Compose `http://127.0.0.1:8000` 결과를 `AIQA_RISK_API_URL` 대상으로 바꾸어
쓰지 않습니다. 대상 URL이 없으면 `operational_deployment_scope=target_pending`을
유지하고 identity를 만들지 않습니다.

### 2-1. baseline, Candidate B, rollback overlay가 승인된 identity만 선택하는지 판단한다

overlay를 읽기 전에 선택될 모델 identity를 예측하고 다음 정적 계약 검사를
실행합니다.

```bash
uv run pytest -q tests/integration/deployment/test_kubernetes_contract.py \
  -k candidate_and_rollback_overlays_select_only_approved_models
```

Candidate A가 overlay에 없고 승인된 identity만 선택되는지 기록합니다. 이미지
digest는 실행 코드와 환경을, 모델 SHA-256은 학습 결과 파일을 식별하므로 두
지문을 하나로 합치지 않습니다. 정적 검사는 target sync PASS가 아닙니다.

### 2-2. 이미 등록된 Application을 Candidate B로 바꾸고 대상 `/v1/model`을 확인한다

수강생 VM의 hostPath `/mnt/course-models`에 승인된 Candidate B 묶음을 게시하고,
플랫폼이 이미 등록한 Application만 Candidate B overlay로 동기화합니다.
Application을 만들지 않으며 automated prune/selfHeal을 켜지 않습니다. 학생 VM
destination은 `kubernetes.default.svc`가 아니어야 합니다. 클러스터를 바꾸는
명령은 문서화된 스크립트가 승인된 컨텍스트를 확인한 뒤에만 실행합니다. 가드
문구는 [`deploy/argocd/README.md`](../../../deploy/argocd/README.md)를 따릅니다.

```bash
uv run python scripts/platform/publish_model.py candidate-b --revision v2 --target-root /mnt/course-models
uv run python scripts/platform/sync_student_release.py \
  --application-name "${AIQA_ARGOCD_APPLICATION_NAME:?already-registered Application name}"
curl "${AIQA_RISK_API_URL:?Risk API base URL is required}/v1/model"
uv run jupyter nbconvert --to notebook --execute \
  labs/chapters/ch03/02_release_candidate_b.ipynb \
  --output /tmp/ch03-candidate-b.ipynb \
  --ExecutePreprocessor.timeout=120
```

`/v1/model`의 `version`은 `candidate-b-c712a8e52344`와 같아야 합니다. URL이
없거나 200이 아니면 identity를 만들지 않고 `API_NOT_RUNNING`과
`operational_deployment_scope=target_pending`, `result=BLOCKED`와 사유를
기록합니다. 이 확인이 통과해도 sealed test를 다시 평가한 것이 아니며 공식
평가 결과를 바꾸지 않습니다. 강사 화면이 있으면 목표 상태, Git 반영(`Synced`),
준비 상태(`Healthy`), 실제 요청 성공의 네 단계 가운데 확인한 단계와 확인하지
못한 단계를 나눕니다. `Synced`만으로 요청 성공을 말하지 않습니다.

이 작업 트리에서는 공유 Argo에 대한 live sync를 실행하지 못했습니다. 수강생
VM에서 기존 Application 동기화 결과가 없으면 대상 운영 scope는
`operational_deployment_scope=target_pending`으로 남기고, 실행이 막힌 경우에는
`result=BLOCKED`와 사유, 담당자를 기록합니다.

### 2-3. Application 생성, KServe 설치, rollback Demo는 플랫폼 범위로 남긴다

KServe 설치, GHCR pull secret, Argo Application 생성은 강사와 플랫폼
책임입니다. rollback overlay 전환과 KServe health Demo도 플랫폼 범위입니다.
결과가 없으면 운영 scope는 `target_pending`으로 남기고, 실행이 막힌 경우에는
별도 execution result인 `result=BLOCKED`와 사유, 담당자를 기록합니다. 정적
overlay는 `scope=static`인 복구 의도이지 rollback 완료가 아닙니다.

## 3. 단계 완료

판단 기록의 서빙 확인 칸에 API 응답, model metadata, 정적 manifest와 실제 대상 환경에서 아직
확인하지 못한 범위를 나눠 기록합니다. 다음 **관측** 단계는 같은 model identity와
환경과 시간 범위를 기준으로 telemetry 조건을 먼저 정합니다.
