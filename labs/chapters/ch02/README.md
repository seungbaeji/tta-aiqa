# 2장 모델 품질

이 장은 1장에서 확인한 데이터 범위 위에서 후보를 보류할지 승인할지 정하고,
그 판단이 어떤 데이터와 실험 기록에 붙는지 확인합니다.

## 1. 본편 실습

공식 평가 결과를 다시 튜닝하지 않습니다. 개발용 수치와 후보 공식 평가를 한
표에 섞지 않습니다.

### 1-1. Precision, Recall, F1, FP/FN과 PR-AUC를 같은 release 질문으로 해석한다

`00_train_valid_model_walkthrough.ipynb`를 실행하기 전에, 정확도 하나만으로
판단할 때 생길 오류를 예측합니다. 노트북은 학습 2,900건과 검증 600건만
사용합니다. 개발용 정확도 0.8550, 재현율 0.2169, 미탐 65를 후보 공식 결과와
섞지 않습니다. 각 지표가 어떤 보호 질문에 답하는지 기록합니다.

### 1-2. 검증 시점 근거로 후보 선택 논리를 추적한다

`00b_trace_valid_model_selection.ipynb`를 위에서 아래로 실행합니다. 학습하지
않고 `profiles.yaml`과 `development-benchmark.json`만 읽습니다. 슬라이드의
선택은 GridSearch가 아니며 봉인 test로 고르는 것도 아닙니다. 후보는 이미
프로필에 고정되어 있고, 이 검증 숫자는 공식 승인이 아닙니다.

### 1-3. Candidate A는 HOLD이고 Candidate B는 APPROVE인지 canonical benchmark로 판정한다

다음 명령으로 고정된 모델 상태를 확인합니다.

```bash
uv run python labs/run/model_status.py --revision v2
```

`docs/evidence/model-v2/canonical-benchmark.json`과
`release-manifest.json`에서 Candidate A는 보류, Candidate B는 승인으로
기록합니다. B의 승인은 대상 배포 완료가 아닙니다. 공식 평가에 맞춰
특성, 임계값, 배포 정책을 바꾸지 않습니다.

`01_compare_model_evidence.ipynb`를 위에서 아래로 실행하면 특성, 프로필,
정책, PR-AUC, 정밀도, 재현율, 미탐과 보호 기준의 연결을 같은 범위에서 읽을
수 있습니다.

### 1-4. DVC revision과 MLflow run이 같은 model evidence lineage를 가리키는지 확인한다

`02_trace_model_lineage.ipynb`를 위에서 아래로 실행합니다. 이 노트북 하나에서
**DVC → MLflow Run → 모델 묶음 → release manifest** 순서로 Candidate B를
추적합니다. Git commit, 데이터 revision과 역할별 SHA-256, 모델 Run과 최종 Run,
`model.joblib`과 `metadata.json`, feature contract SHA-256을 한 표에서
연결합니다.

과거 model Run `31b50eb...`은 실제 MLflow export가 아니라 준비된 여러 JSON을
profile 이름으로 연결한 역사적 reconstruction입니다. 당시 frozen DVC lock
원본과 clean worktree는 복원할 수 없으므로 완전 재현이라고 설명하지 않습니다.
확인된 데이터·metric·bundle 지문과 복원 불가능한 범위는 노트북의 첫 표에서
함께 봅니다.

현재 학생 Run은 관찰 가능한 정상 개발 기록을 새로 만듭니다. 학생 Run은
Candidate B, train 2,900건, valid 600건, Random Forest와 임계값 0.35를 사용하고
dataset input, parameter, validation metric, bundle 두 파일과 MLflow Logged
Model을 experiment `student-development-tracking`에 기록합니다. 같은
train/valid 파일의 revision, 경로, 행 수와 SHA-256을 검증한 뒤 학습과 MLflow
입력에 함께 사용하며, 공식 승인이나 봉인 평가를 바꾸지 않습니다.

강의 전 이미지 build, bind mount 권한, 화면별 설명 순서와 Teach-back 질문은
[`INSTRUCTOR_GUIDE.md`](INSTRUCTOR_GUIDE.md)를 먼저 확인합니다.

닫힌망 수강생의 MLflow는 Compose입니다. 강사가 준 공개 URL을
`AIQA_MLFLOW_TRACKING_URI`로 설정합니다. 수강생은 ClusterIP, port-forward,
tunnel을 만들지 않습니다. `http://127.0.0.1:5000`은 닫힌망 기본 경로가
아닙니다.

```bash
docker compose -f deploy/compose.yaml up -d --no-build --wait mlflow
curl "${AIQA_MLFLOW_TRACKING_URI%/}/health"
uv run jupyter nbconvert --to notebook --execute \
  labs/chapters/ch02/02_trace_model_lineage.ipynb \
  --output /tmp/ch02-model-lineage.ipynb \
  --ExecutePreprocessor.timeout=600
```

노트북은 내부에서 [`labs/run/log_development.py`](../../run/log_development.py)를
한 번 호출하고 방금 만든 Run을 API로 다시 조회합니다. 값이 없거나 `/health`가
실패하면 `MLFLOW_NOT_RUNNING`으로 멈추되, 역사적 JSON 연결 표와 코드 읽기
순서는 끝까지 확인할 수 있습니다. MLflow 화면의 Tags, Parameters, Metrics,
Datasets, Artifacts와 Logged Models를 각각 실제 logging API와 연결합니다.
학생 client는 `artifacts/mlflow/`에 직접 쓰지 않지만 Compose MLflow server는
받은 Run과 artifact를 그 bind mount에 지속합니다. DVC 또는 MLflow 개별 API
문법이 더 필요할 때만 Appendix 09와 13을 참고합니다.

## 2. 단계 완료

판단 기록의 모델 품질 칸에 후보별 판단, 사용한 공식 경로, 이력 확인 범위를
남깁니다. 다음 장에서는 이 승인을 운영 배포 완료로 확대하지 않고, 실제로
떠 있는 모델 정보를 따로 대조합니다.
