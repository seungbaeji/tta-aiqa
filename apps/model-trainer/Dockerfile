FROM python:3.11-slim

RUN pip install --no-cache-dir uv==0.11.12
WORKDIR /workspace

COPY pyproject.toml uv.lock ./
COPY apps ./apps
COPY packages ./packages
RUN uv sync --frozen --no-dev --package aiqa-model-trainer

ENV PATH="/workspace/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

USER 65532:65532
EXPOSE 5000
