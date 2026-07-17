# 5장 배포 판단

## 1. 입력 분포를 먼저 확인하기

기준 모델의 `high_risk` 예측 비율이 늘었다면 모델부터 탓하지 않고 입력 조건이 달라졌는지 확인합니다. `00_compare_input_distributions.ipynb`는 정답이 없는 운영 요청 표본과 `current-shift` 설정을 읽어 네 특성의 평균과 중앙값을 비교합니다.

```bash
uv run jupyter nbconvert --to notebook --execute \
  labs/ch05-release-decision/00_compare_input_distributions.ipynb \
  --output /tmp/ch05-input-distribution.ipynb \
  --ExecutePreprocessor.timeout=120
```

이 결과는 준비된 표본의 입력 변화 후보를 강화하지만 새 모델 성능이나 실제 대상 환경의 상태를 확정하지 않습니다. 대상 환경의 같은 모델 정보와 시간 범위에서 점수, 예측 분포와 대표 요청을 더 확인해야 합니다.

## 2. 모델 승인과 운영 상태를 나누기

이 실습은 Candidate B를 무조건 대상 환경에 배포하는 과정이 아닙니다. Candidate A=`HOLD`, Candidate B=`APPROVE`라는 공식 모델 평가와 실제 실행 환경, 운영 관측 결과를 한 기록에 모으되 두 판단을 별도로 씁니다.

| 판단 항목 | 현재 자료에서 쓸 수 있는 값 | 대상 환경에서 더 확인할 근거 |
| --- | --- | --- |
| 모델 승인 | A=`HOLD`, B=`APPROVE`, `deployment_allowed=true` | 새로운 봉인 평가가 없으면 변경하지 않음 |
| 운영 배포 상태 | 배포 설정과 오버레이의 정적 검사, 로컬 노트북 결과 | GitOps 동기화, 대상 API 모델 정보, 요청과 운영 기록의 시간 범위 |
| 현재 권고 | 대상 환경 근거 수집 | 확인한 범위에 맞는 제한적 배포 또는 되돌리기 검토 |

대상 클러스터나 Grafana Cloud를 보지 못했다면 Candidate B의 모델 승인을 바꾸지 않고 `operational_deployment_scope=target_pending`으로 남깁니다.

## 3. 배포 연결과 판단 노트북 확인하기

현재 모델 평가 상태와 배포 연결 검사를 실행합니다. 파일 경로의 `v2`는 내부 개정본 이름이며 과정 명칭이 아닙니다.

```bash
uv run python scripts/run_model.py status --revision v2
uv run pytest -q \
  tests/integration/qa/test_v2_serialized_bundle_verification.py \
  tests/integration/deployment/test_kubernetes_contract.py
```

`01_review_release_decision.ipynb`는 공식 평가, 배포 선언, 기준 모델, Candidate B와 되돌리기 오버레이를 대조합니다. URL이 없을 때 `URL_NOT_CONFIGURED`와 `target_pending`이 나오는 것은 예상한 결과입니다. Candidate A는 어떤 배포 오버레이에도 포함되지 않아야 합니다.

강사 환경에 모델 저장 위치가 준비된 경우에만 Candidate B 모델 묶음을 게시합니다. 출력 경로의 `candidate-b-c712a8e52344`와 `deployment.json`의 프로필, SHA-256을 기록합니다. 이 결과는 모델 묶음을 준비했다는 근거이며 대상 PVC 탑재나 API 응답을 뜻하지 않습니다.

```bash
uv run python scripts/publish_model.py candidate-b \
  --revision v2 \
  --target-root /mnt/course-models
```

## 4. 대상 환경과 되돌리기 조건 확인하기

대상 연결 이름을 정확히 제공받은 경우에만 서버 측 검사를 실행합니다. 실제 Candidate B 동기화는 강사가 안내한 GitOps, Argo CD 절차에서만 수행합니다.

```bash
kubectl config current-context
kubectl kustomize deploy/kubernetes/overlays/candidate-b >/tmp/tta-aiqa-candidate-b.yaml
kubectl apply --dry-run=server -f /tmp/tta-aiqa-candidate-b.yaml
```

대상 `/v1/model`의 프로필, 해시값, 임계값, 정상 요청 응답, 요청 시나리오, 대시보드 URL과 조회 시간 범위를 기록합니다. API 프로필 하나나 HTTP 200 한 건만으로 `target_verified`라고 쓰지 않습니다.

되돌리기 오버레이는 기준 모델로 돌아갈 설정을 선언할 뿐 복구 완료를 증명하지 않습니다. 예상 Candidate B와 다른 모델 정보, 규약에 맞는 요청의 실패, 담당자가 확인한 운영 조건은 되돌리기 검토를 열 수 있습니다. 의도한 무효 요청의 422와 자격 증명 누락은 자동 되돌리기 조건이 아닙니다.

## 5. 제출물

최종 기록에는 확인한 범위, 근거 목록, 원인 후보, 모델 승인, 운영 배포 상태, 현재 권고, 승인, 보류 위험, 담당자와 재평가 조건이 있어야 합니다.

> Candidate A는 공식 평가에서 `HOLD`, Candidate B는 `APPROVE`입니다. Candidate B 배포 설정의 프로필과 해시값은 [정적/로컬/대상 범위]에서 확인했지만 [대상 GitOps/API 모델 정보/운영 기록]은 [확인 또는 미확인]입니다. 따라서 운영 배포 상태는 [prepared/local_verified/target_verified/target_pending/rollback_required], 현재 권고는 [대상 근거 수집/제한적 배포/보류/되돌리기 검토]입니다. [담당 팀]이 [다음 자료]를 [기한]까지 수집하면 다시 판단합니다.
