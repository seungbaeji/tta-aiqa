"""Shared helpers for chapter 3 serving labs."""

from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi.testclient import TestClient

from ai_quality.common.config import load_yaml
from ai_quality.common.paths import config_path, data_path
from ai_quality.serving.infrastructure.fastapi_app import create_app


def load_yaml_config(*parts: str) -> dict[str, Any]:
    """Load one YAML config file."""
    return load_yaml(config_path(*parts))


def build_test_client() -> TestClient:
    """Build an in-process FastAPI test client."""
    return TestClient(create_app())


def load_serving_payload() -> dict[str, Any]:
    """Load one example serving request payload."""
    request_path = data_path("serving_requests_valid.csv")
    if not request_path.exists():
        msg = (
            f"Dataset not found: {request_path}\n"
            "Run: uv run python labs/prepare_data.py"
        )
        raise FileNotFoundError(msg)

    dataframe = pd.read_csv(request_path)
    record = dataframe.head(1).to_dict(orient="records")[0]
    payload = {str(key): value for key, value in record.items()}
    payload["request_id"] = "lab-03-request-001"
    return payload
