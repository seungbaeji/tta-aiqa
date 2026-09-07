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
