FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PATH="/workspace/.venv/bin:${PATH}"

WORKDIR /workspace

COPY --from=ghcr.io/astral-sh/uv:0.7.21 /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
COPY packages ./packages
COPY apps/simple_mlops/pyproject.toml apps/simple_mlops/uv.lock ./apps/simple_mlops/
ARG UV_SYNC_GROUPS=""
RUN uv sync --project apps/simple_mlops --frozen --no-dev ${UV_SYNC_GROUPS}

WORKDIR /app

COPY apps/simple_mlops/app.py apps/simple_mlops/config.py apps/simple_mlops/train.py apps/simple_mlops/send_fake_traffic.py ./
COPY apps/simple_mlops/config ./config

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
