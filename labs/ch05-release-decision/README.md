# 5장 배포 판단

## 1. P5 수집 묶음에서 P7 판단까지 이어가기

마지막 세 교시는 같은 운영 근거를 역할만 바꾸어 사용합니다.
P5 인계 자료는 live 수집 매니페스트(collection manifest)
`artifacts/traffic/collection-session.json` 또는 offline 수집 묶음
`docs/reference/evidence/incident/prepared-observability-correlation.json`
가운데 하나입니다. 두 파일의 스키마는 다르지만 환경·모델·세 run ID·절대 UTC
범위라는 공통 의미를 이어받습니다.

| 교시 | 근거 소유 | 이 장에서 이어받을 결과 |
| --- | --- | --- |
| P5 수집 | 팀 공유 | 인계 자료의 유형·ID·경로, 환경, 모델, UTC 범위, 시나리오별 run ID와 누락 신호 |
| P6 분석 | 개인 | 같은 수집 묶음에서 본 관측·해석·한계·다음 확인 |
| P7 추적·판단 | 개인 | 대표 request ID·trace ID가 최종 권고를 바꾼 이유 |

P5 뒤에는 Compose를 내리지 않습니다. P6의 범위 복원·세 시나리오 비교·대표 요청
선택과 P7 추적·판단이 끝날 때까지 같은 시간 범위와 run ID를 보존합니다.
시나리오별 응답은
`artifacts/traffic/compose.jsonl`에서 다시 찾습니다. 실시간 환경이 없으면
`docs/reference/evidence/incident/prepared-observability-correlation.json`의
`OBS-FALLBACK-02`를 팀 수집 묶음으로 사용하되, `scope=static`과 실제 수집을
확인하지 못한 이유를 적습니다.

팀 수집 묶음은 공유해도 D2-P6 분석 행과 전이 사건 T-01은 개인별로 작성합니다.
P7에서는 P6에서 고른 대표 요청을 그대로 사용하며 새 트래픽을 보내지 않습니다.

## 2. 누적 기록과 출발 근거 확인하기

개인 작업본 `artifacts/reports/release-decision-record.md`를 열고 앞 장의 근거가
남아 있는지 확인합니다. 파일이 없다면 기존 기록이 없는지 확인한 뒤 한 번만
초기화합니다.

```bash
mkdir -p artifacts/reports
test -f artifacts/reports/release-decision-record.md || \
  cp labs/release-decision-record.md \
    artifacts/reports/release-decision-record.md
```

`docs/reference/evidence/incident/initial-signal.json`은 첫 교시에서 제공한 준비된
E-01 근거입니다. 실제 Grafana 관측과 섞지 말고, 이 장에서 수집한 run ID, 시간
범위와 URL은 별도 행에 추가합니다.

## 3. 입력 분포를 먼저 확인하기

기준 모델의 `high_risk` 예측 비율이 늘었다면 모델부터 탓하지 않고 입력 조건이 달라졌는지 확인합니다. `00_compare_input_distributions.ipynb`는 정답이 없는 운영 요청 표본과 `current-shift` 설정을 읽어 네 특성의 평균과 중앙값을 비교합니다.

```bash
uv run jupyter nbconvert --to notebook --execute \
  labs/ch05-release-decision/00_compare_input_distributions.ipynb \
  --output /tmp/ch05-input-distribution.ipynb \
  --ExecutePreprocessor.timeout=120
```

이 결과는 준비된 표본의 입력 변화 후보를 강화하지만 새 모델 성능이나 실제 대상 환경의 상태를 확정하지 않습니다. 대상 환경의 같은 모델 정보와 시간 범위에서 점수, 예측 분포와 대표 요청을 더 확인해야 합니다.

## 4. 모델 승인과 운영 상태를 나누기

이 실습은 Candidate B를 무조건 대상 환경에 배포하는 과정이 아닙니다. Candidate A=`HOLD`, Candidate B=`APPROVE`라는 공식 모델 평가와 실제 실행 환경, 운영 관측 결과를 한 기록에 모으되 두 판단을 별도로 씁니다.

| 판단 항목 | 현재 자료에서 쓸 수 있는 값 | 대상 환경에서 더 확인할 근거 |
| --- | --- | --- |
| 모델 승인 | A=`HOLD`, B=`APPROVE`, `deployment_allowed=true` | 새로운 봉인 평가가 없으면 변경하지 않음 |
| 운영 환경 확인 상태 | 배포 설정과 오버레이의 정적 검사, 로컬 노트북 결과 | GitOps 동기화, 대상 API 모델 정보, 요청과 운영 기록의 시간 범위 |
| 현재 권고 | 대상 환경 근거 수집 | 확인한 범위에 맞는 제한적 배포 또는 되돌리기 검토 |

대상 클러스터나 Grafana Cloud를 보지 못했다면 Candidate B의 모델 승인을 바꾸지 않고 `operational_deployment_scope=target_pending`으로 남깁니다.

## 5. 배포 연결과 판단 노트북 확인하기

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

## 6. 대상 환경과 되돌리기 조건 확인하기

Candidate B와 되돌리기 오버레이를 로컬에서 펼쳐 프로필·전체 SHA-256·고정 경로를
대조합니다. 수강생은 클러스터에 서버 요청을 보내거나 실제 동기화·되돌리기를
수행하지 않습니다.

```bash
kubectl kustomize deploy/kubernetes/overlays/candidate-b >/tmp/tta-aiqa-candidate-b.yaml
kubectl kustomize deploy/kubernetes/overlays/rollback >/tmp/tta-aiqa-rollback.yaml
```

대상 `/v1/model`의 프로필·버전·임계값과 정상 요청 응답을 기록하고, 배포 선언 파일·오버레이에서는 전체 SHA-256 해시값을 따로 기록합니다. 요청 시나리오, 대시보드 URL과 조회 시간 범위도 함께 남깁니다. API 프로필 하나나 HTTP 200 한 건만으로 `target_verified`라고 쓰지 않습니다.

되돌리기 오버레이는 기준 모델로 돌아갈 설정을 선언할 뿐 복구 완료를 증명하지 않습니다. 예상 Candidate B와 다른 모델 정보, 규약에 맞는 요청의 실패, 담당자가 확인한 운영 조건은 되돌리기 검토를 열 수 있습니다. 의도한 무효 요청의 422와 자격 증명 누락은 자동 되돌리기 조건이 아닙니다.

## 7. 제출물

개인별 `artifacts/reports/release-decision-record.md`를 제출합니다. 제출 전에는
14교시 행, E-01~E-05, P5 팀 수집 묶음 ID, P6 개인 분석, 모델 승인과 운영 배포
상태, 현재 권고, 담당자와 재평가 조건, 개인 T-01이 있는지만 확인합니다.

> Candidate A는 공식 평가에서 `HOLD`, Candidate B는 `APPROVE`입니다. Candidate B 배포 설정의 프로필과 해시값은 [정적/로컬/대상 범위]에서 확인했지만 [Candidate B API 모델 정보/같은 모델의 운영 기록]은 [확인 또는 미확인]입니다. 따라서 운영 환경 확인 상태는 [prepared/local_verified/target_verified/target_pending/rollback_required]입니다. `local_verified`는 Candidate B를 실제 로컬 서빙하고 같은 모델의 요청·운영 자료까지 확인했을 때만 사용합니다. 현재 권고는 [대상 근거 수집/제한적 배포/보류/되돌리기 검토]이며, [담당 팀]이 [다음 자료]를 [기한]까지 수집하면 다시 판단합니다.
