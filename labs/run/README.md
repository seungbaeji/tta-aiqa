# 여정 본편 실행 모듈

이 폴더의 모듈만 9단계 여정의 본편 명령입니다. 수강생이 코드를 채우는 작은
구현은 [`labs/exercises/`](../exercises/README.md)에 있고, 환경 준비와 공식
evidence 생성, 강사/플랫폼 도구는 `scripts/`에 있습니다.

```bash
uv run python labs/run/prepare_data.py
uv run python labs/run/validate_data.py
uv run python labs/run/model_status.py
uv run python labs/run/log_development.py
```

`log_development.py`는 학습/검증만 사용하는 Candidate B 개발 학습을 교실
Compose MLflow의 experiment `student-development-tracking`에 남깁니다.
`split-revision.json`의 revision, 경로, 행 수와 SHA-256을 먼저 확인하고, 검증된
`train.csv`와 `valid.csv`를 학습과 MLflow dataset input에 동일하게 사용합니다.
Random Forest 설정과 임계값, 검증 지표, `model.joblib`, `metadata.json`과 MLflow
Logged Model을 한 Run에 기록합니다. Git commit, DVC lock, data-lineage,
train/valid와 feature contract SHA-256도 같은 Run의 provenance로 남깁니다.

공식 실행 번호는 `docs/evidence/model-v2/release-manifest.json`에 이미
있습니다. 이 명령은 그 번호를 새로 만들지 않으며 봉인 평가와 operational
역할도 쓰지 않습니다. 공식 근거 폴더에는 쓰지 않습니다. 학생 client가
`artifacts/mlflow/`를 직접 수정하지는 않지만, Compose MLflow server는 전달받은
Run metadata와 artifact를 그 bind mount에 지속합니다.

강사가 준 `AIQA_MLFLOW_TRACKING_URI`가 없거나 `/health`가 실패하면
`MLFLOW_NOT_RUNNING`만 남기고 실행을 만들지 않습니다. sqlite나
`http://127.0.0.1:5000` 기본값을 쓰지 않습니다. 화면이 비어 있어도 공식
판단은 JSON으로 가능합니다. 출력된 학생 실행 번호는 공식 학습 실행이나
공식 승인 실행을 대체하지 않습니다. 판단 기록의 모델 품질 칸에는 공식 JSON
경로와 공식 실행 번호를 유지합니다.
