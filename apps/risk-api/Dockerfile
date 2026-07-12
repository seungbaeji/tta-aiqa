FROM python:3.11-slim

ARG VCS_REF=unknown
LABEL org.opencontainers.image.source="https://github.com/seungbaeji/tta-aiqa" \
      org.opencontainers.image.revision="${VCS_REF}"

RUN pip install --no-cache-dir uv==0.11.12
WORKDIR /workspace

COPY pyproject.toml uv.lock ./
COPY apps ./apps
COPY packages ./packages
RUN uv sync --frozen --no-dev --package aiqa-risk-api

ENV PATH="/workspace/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

USER 65532:65532
EXPOSE 8000
CMD ["uvicorn", "risk_api.main:create_runtime_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
