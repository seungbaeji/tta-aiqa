# 3장 서빙 환경 확인

## 1. 목표와 확인 범위

이 실습은 API 응답 여부보다 실제로 확인한 모델 정보와 배포 설정이 같은 모델을 가리키는지 살펴봅니다. Compose는 로컬 scikit-learn 어댑터를 사용하고 Kubernetes는 KServe HTTP 어댑터를 사용하지만, 외부에 공개하는 Risk API 규약은 같아야 합니다.

Candidate B의 `APPROVE`는 2장의 공식 모델 평가 결과입니다. 대상 환경의 모델 정보를 확인하지 못했다는 이유로 이 결과를 `HOLD`로 바꾸지 않고, 운영 환경 확인 상태만 확인한 범위에 맞춰 적습니다.

| 확인 범위 | 이 실습에서 확인할 수 있는 근거 | 아직 말할 수 없는 내용 |
| --- | --- | --- |
| `prepared` | 게시한 모델 묶음, 펼친 배포 설정, 노트북의 정적 검사 | 대상 클러스터가 실행 중임 |
| baseline `scope=local` | 기본 로컬 `/health/ready`, `/v1/model`, 정상 200과 의도한 422 | Candidate B가 로컬 또는 대상 환경에서 실행 중임 |
| `target_pending` | Docker, `kubectl`, 대상 URL이 없어 실제 결과를 보지 못함 | 대상 배포의 성공 또는 실패 |

## 2. 기준 모델과 로컬 API 실행

강사가 준비한 기준 모델 묶음의 배포 기록을 확인합니다. `deployment.json`의
`profile`과 모델 SHA-256은 로컬 마운트가 읽을 모델을 가리키며, 대상 환경의 배포
성공을 뜻하지 않습니다.

```bash
cat artifacts/models/revisions/v2/deployed/deployment.json
```

강사가 준비한 Risk API 이미지를 시작한 뒤 준비 상태와 모델 정보를 확인합니다.
같은 API에 기준 요청과 의도적으로 잘못 만든 요청을 보내 정상 200과
`MODEL_INPUT_INVALID` 422를 구분합니다. 이미지 빌드는 수강생 활동에 포함하지
않습니다.

```bash
docker compose -f deploy/compose/simple-mlops/compose.yaml up -d risk-api
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/v1/model
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm \
  --user "$(id -u):$(id -g)" \
  traffic-generator baseline --count 20 --fast
docker compose -f deploy/compose/simple-mlops/compose.yaml \
  --profile traffic run --rm \
  --user "$(id -u):$(id -g)" \
  traffic-generator invalid --count 3 --fast
```

여기서 `--fast`는 로컬 API의 200과 422만 빠르게 확인합니다. Grafana의
`rate()` 근거는 4장에서 Alloy override와 기본 수집 간격을 사용해 따로 만듭니다.

`/v1/model`의 프로필, 버전, 임계값과 출력된 run ID를 기록합니다. 이 명령은
응답 헤더를 화면이나 파일에 보존하지 않으므로, 요청 ID는
`artifacts/traffic/*.jsonl`의 `request_id`와 응답 본문의 `request_id`에서
확인합니다. run ID는 한 번의 실행을, 요청 ID는 그 안의 한 요청을 JSONL, 로그,
추적 기록에서 찾는 값입니다. 두 식별자는 Prometheus 지표 레이블로 사용하지
않습니다.

Docker가 없거나 API가 시작하지 않으면 다음 노트북의 정적 검사만 실행합니다. 없는 API 응답을 재현한 것처럼 쓰지 않고 `prepared` 또는 `target_pending`으로 기록합니다.

## 3. 노트북과 Kubernetes 설정 확인

`01_verify_risk_api.ipynb`는 정답 없는 운영 요청의 133개 특성과 Kubernetes 배포 설정을 검사합니다. 다른 로컬 URL을 사용하면 `AIQA_RISK_API_URL`을 지정합니다. `API_NOT_RUNNING`은 정적 검사 실패가 아니라 실제 API 근거가 없다는 상태입니다.

수강생은 클러스터에 요청을 보내거나 배포 명령을 다루지 않습니다. 다음 계약
검사로 Candidate B와 되돌리기 선언이 승인된 모델만 가리키는지 확인합니다.
실제 동기화와 서버 측 검사는 플랫폼 담당자가 수행합니다.

```bash
uv run pytest -q tests/integration/deployment/test_kubernetes_contract.py \
  -k candidate_and_rollback_overlays_select_only_approved_models
```

## 4. 완료 기준

최종 기록에는 확인한 환경, API가 반환한 모델 프로필·버전·임계값, 배포 선언 파일의 전체 SHA-256 해시값, 정상·무효 요청 결과, 아직 빠진 대상 환경 근거를 구분해 씁니다. 기준 모델의 로컬 200과 422를 Candidate B 대상 환경의 근거로 바꾸지 않습니다.

> 기존 운영 모델의 증거 범위는 [`prepared`/`scope=local`]이고, Candidate B의 운영 환경 확인 상태는 `target_pending`입니다. [파일/API/배포 설정]에서 [프로필, 버전 또는 해시값]을 확인했고, 정상·무효 요청은 [실행 결과 또는 실행하지 못한 이유]로 기록했습니다. Candidate B의 모델 `APPROVE`는 유지하되 [Candidate B 모델 정보와 같은 모델의 요청·운영 자료]는 [담당 팀]이 확인할 때까지 배포 결론으로 넓히지 않습니다.

4장에서는 같은 모델 정보를 전제로 요청 시나리오와 운영 기록을 확인합니다. 입력, API, 실행 환경 가운데 어느 원인 후보가 강화되는지 기록합니다.
