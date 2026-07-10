FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.7.21 /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
ARG UV_SYNC_GROUPS=""
RUN uv sync --frozen --no-dev ${UV_SYNC_GROUPS}

COPY app.py config.py train.py send_fake_traffic.py ./
COPY config ./config

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
