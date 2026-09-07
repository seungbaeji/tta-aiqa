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
uv run python scripts/run_model.py status --revision v2
```

`docs/reference/evidence/model/revisions/v2/canonical-benchmark.json`과
`release-manifest.json`에서 Candidate A는 보류, Candidate B는 승인으로
기록합니다. B의 승인은 대상 배포 완료가 아닙니다. 공식 평가에 맞춰
특성, 임계값, 배포 정책을 바꾸지 않습니다.

`01_compare_model_evidence.ipynb`를 위에서 아래로 실행하면 특성, 프로필,
정책, PR-AUC, 정밀도, 재현율, 미탐과 보호 기준의 연결을 같은 범위에서 읽을
수 있습니다.

### 1-4. DVC revision과 MLflow run이 같은 model evidence lineage를 가리키는지 확인한다

`model-bootstrap.json`, `release-freeze.json`, `canonical-benchmark.json`,
`release-manifest.json`의 순서와 데이터 revision, 파일 지문, 실험 실행 번호를
대조합니다. 닫힌망 수강생의 MLflow는 클러스터 Ingress입니다. 강사가 준 URL을
`AIQA_MLFLOW_TRACKING_URI`로 설정합니다. 수강생은 ClusterIP, port-forward,
tunnel을 만들지 않습니다. Compose `http://127.0.0.1:5000`은 닫힌망 기본
경로가 아닙니다. 값이 없거나 `/health`가 실패하면 JSON을 읽고 화면 미확인을
따로 적습니다.

```bash
curl "${AIQA_MLFLOW_TRACKING_URI%/}/health"
```

## 2. 남는 시간 실습

판단 기록의 모델 품질 칸에 공식 실행 번호를 적은 뒤에만 엽니다. 화면이 비어
있어도 공식 판단은 JSON으로 이미 닫혀 있습니다.

### 2-1. 개발용 학습을 클러스터 MLflow run으로 남겨 공식 실행과 구분한다

1장 선택 노트북 `02_inspect_dvc_revision_practice.ipynb`에서 학습/검증 지문을
확인한 뒤에만 엽니다. 선택 노트북
`02_log_development_mlflow_run_practice.ipynb`를 위에서 아래로 실행합니다.
학습/검증만 사용하는 개발용 학습을 `AIQA_MLFLOW_TRACKING_URI`의 클러스터
MLflow experiment `practice-development-tracking`에 남깁니다. 값이 없거나
`/health`가 실패하면 `MLFLOW_NOT_RUNNING`만 남기고 실행을 만들지 않습니다.
이 실행 번호는 공식 학습 실행이나 공식 승인 실행을 대체하지 않으며, 공식
근거 폴더와 `artifacts/mlflow/`에도 쓰지 않습니다.

## 3. 단계 완료

판단 기록의 모델 품질 칸에 후보별 판단, 사용한 공식 경로, 이력 확인 범위를
남깁니다. 다음 장에서는 이 승인을 운영 배포 완료로 확대하지 않고, 실제로
떠 있는 모델 정보를 따로 대조합니다.
