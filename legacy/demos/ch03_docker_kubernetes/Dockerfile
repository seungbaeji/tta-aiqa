FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY packages ./packages
COPY configs ./configs
COPY artifacts/models/chapter_02_baseline.pkl ./artifacts/models/chapter_02_baseline.pkl

RUN uv sync --frozen --group lab --no-dev

ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV MODEL_PATH=artifacts/models/chapter_02_baseline.pkl
ENV MODEL_VERSION=v1
ENV MODEL_THRESHOLD=0.5
ENV EVENT_LOG_PATH=artifacts/logs/prediction_events.jsonl

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "python", "-m", "ai_quality.serving.infrastructure.fastapi_app"]
