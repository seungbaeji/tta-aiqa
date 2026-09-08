# 여정 본편 실행 모듈

이 폴더의 모듈은 데이터 준비, 품질 확인, 공식 Candidate B 읽기처럼 장별
노트북 밖에서 한 번 실행하는 본편 명령입니다. 수강생이 코드를 채우는 작은
구현은 [`labs/exercises/`](../exercises/README.md)에 있고, 환경 준비와 공식
evidence 생성, 강사/플랫폼 도구는 `scripts/`에 있습니다.

데이터 준비, 품질 확인, 공식 Candidate B 읽기는 1장과 2장 앞 단계에서 이미
끝냅니다.

```bash
uv run python labs/run/prepare_data.py
uv run python labs/run/validate_data.py
uv run python labs/run/model_status.py --revision v2
```

## 학생 MLP

2장 본편은 노트북
[`03_log_student_mlp.ipynb`](../chapters/ch02/03_log_student_mlp.ipynb)입니다.
공식 승인은 Candidate B Random Forest입니다. 학생 MLP(`candidate-c`)는 같은
v2 train/valid로 iteration 곡선을 관찰하기 위한 개발 실행이며, 공식 승인이나
봉인 평가를 바꾸지 않습니다.

노트북은 [`development.yaml`](development.yaml)과
[`student-profiles.yaml`](../../configs/model-v2/student-profiles.yaml)을
딕셔너리로 읽고, pandas로 train 2,900행과 valid 600행만 연 뒤 sklearn
`MLPClassifier`를 iteration마다 학습합니다. `split-revision.json`의
revision, 경로, 행 수, SHA-256을 먼저 확인합니다. 교실 MLflow가 켜져 있으면
`train.loss`와 `valid.roc_auc`를 experiment `student-development-tracking`의
Run `student-mlp-train-valid`에 기록합니다.

sealed test와 operational은 열지 않습니다. `docs/evidence/model-v2/`에는
쓰지 않습니다. 강사가 준 `AIQA_MLFLOW_TRACKING_URI`가 없거나 `/health`가
실패하면 표와 그림만 보고 `MLFLOW_NOT_RUNNING`을 남깁니다. sqlite나
`http://127.0.0.1:5000` 기본값을 쓰지 않습니다.

`train.loss`가 내려가는데 `valid.*`가 평평하거나 나빠지면 과적합입니다.
공식 실행 번호는 `docs/evidence/model-v2/release-manifest.json`에 있고, 학생
Run ID는 그 번호를 대체하지 않습니다. 3장 서빙은 Candidate B를 유지합니다.
