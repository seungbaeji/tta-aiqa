"""Runtime settings for the simple MLOps API.

Kubernetes can mount a JSON ConfigMap and point APP_CONFIG_PATH at it. Runtime
overrides can still be provided as environment variables, which take priority.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class AppSettings(BaseSettings):
    """Application settings with env override support."""

    app_config_path: Path | None = Field(default=None, exclude=True)
    model_path: Path = Path("/app/models/latest_model.joblib")
    metadata_path: Path = Path("/app/models/latest_metadata.json")
    events_path: Path = Path("/app/events/predictions.jsonl")
    baseline_data_path: Path = Path("/app/data/serving_requests.csv")
    service_name: str = "ai-quality-serving"
    deployment_environment: str = "training"
    otlp_traces_endpoint: str = ""
    otlp_timeout_seconds: float = 2.0
    client_id: str = "simple-traffic-generator"
    source_system: str = "simple-mlops-demo"
    trace_id_prefix: str = "simple-trace"
    input_distribution_features: tuple[str, ...] = (
        "heart_rate",
        "oxygen_saturation",
    )
    score_buckets: tuple[float, ...] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="forbid",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            init_settings,
            dotenv_settings,
            file_secret_settings,
        )

    @field_validator("input_distribution_features", mode="before")
    @classmethod
    def parse_input_distribution_features(cls, value: Any) -> Any:
        return parse_list(value) if isinstance(value, str) else value

    @field_validator("score_buckets", mode="before")
    @classmethod
    def parse_score_buckets(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [float(item) for item in parse_list(value)]
        return value

    @field_validator("score_buckets")
    @classmethod
    def validate_score_buckets(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if len(value) < 2:
            raise ValueError("score_buckets must contain at least two values")
        return value


def load_settings() -> AppSettings:
    config_values: dict[str, Any] = {}
    config_path = os.getenv("APP_CONFIG_PATH")
    if config_path:
        config_values.update(read_config_file(Path(config_path)))
    return AppSettings(**config_values)


def read_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"APP_CONFIG_PATH does not exist: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("APP_CONFIG_PATH must contain a JSON object")
    return payload


def parse_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
