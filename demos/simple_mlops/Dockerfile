FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.7.21 /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app.py train.py send_fake_traffic.py ./

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
