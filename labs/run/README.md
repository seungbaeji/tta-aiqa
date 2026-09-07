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

`log_development.py`는 학습/검증만 사용하는 개발 학습을 교실 Compose MLflow의
experiment `student-development-tracking`에 남깁니다. 공식 실행 번호는
`docs/evidence/model-v2/release-manifest.json`에 이미 있습니다. 이 명령은
그 번호를 새로 만들지 않으며 `test`와 `operational`도 쓰지 않습니다. 공식
근거 폴더와 `artifacts/mlflow/`에도 쓰지 않습니다.

강사가 준 `AIQA_MLFLOW_TRACKING_URI`가 없거나 `/health`가 실패하면
`MLFLOW_NOT_RUNNING`만 남기고 실행을 만들지 않습니다. sqlite나
`http://127.0.0.1:5000` 기본값을 쓰지 않습니다. 화면이 비어 있어도 공식
판단은 JSON으로 가능합니다. 출력된 학생 실행 번호는 공식 학습 실행이나
공식 승인 실행을 대체하지 않습니다. 판단 기록의 모델 품질 칸에는 공식 JSON
경로와 공식 실행 번호를 유지합니다.
