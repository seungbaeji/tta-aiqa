FROM python:3.11-slim@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93 AS builder

RUN pip install --no-cache-dir uv==0.11.12
WORKDIR /workspace
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

COPY pyproject.toml uv.lock ./
COPY apps ./apps
COPY packages ./packages
RUN uv sync --frozen --no-dev --package aiqa-traffic-generator

FROM python:3.11-slim@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93 AS release

WORKDIR /workspace
ENV PATH="/workspace/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

COPY --from=builder /workspace/.venv /workspace/.venv
COPY --from=builder /workspace/apps /workspace/apps
COPY --from=builder /workspace/packages /workspace/packages
# Editable workspace installs resolve these source trees at runtime.

USER 65532:65532
ENTRYPOINT ["aiqa-traffic"]
CMD ["baseline"]
