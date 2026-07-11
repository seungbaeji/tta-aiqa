"""Runtime settings for serving."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_quality.common.config import load_yaml
from ai_quality.common.paths import config_path, project_root


@dataclass(frozen=True)
class RuntimeSettings:
    """Serving runtime settings from config and environment."""

    host: str
    port: int
    model_path: Path
    model_version: str
    threshold: float
    event_log_path: Path


def resolve_project_path(path_text: str) -> Path:
    """Resolve a project-relative path."""
    path = Path(path_text)
    if path.is_absolute():
        return path
    return project_root() / path


# docs:start read_runtime_settings
def read_runtime_settings(config: dict[str, Any] | None = None) -> RuntimeSettings:
    """Read runtime settings from config and environment variables."""
    values = config or load_yaml(config_path("operations", "serving.yaml"))

    return RuntimeSettings(
        host=str(os.getenv("API_HOST", values["host"])),
        port=int(os.getenv("API_PORT", values["port"])),
        model_path=resolve_project_path(
            os.getenv("MODEL_PATH", values["model_path"])
        ),
        model_version=str(os.getenv("MODEL_VERSION", values["model_version"])),
        threshold=float(os.getenv("MODEL_THRESHOLD", values["threshold"])),
        event_log_path=resolve_project_path(
            os.getenv("EVENT_LOG_PATH", values["event_log_path"])
        ),
    )
# docs:end read_runtime_settings
