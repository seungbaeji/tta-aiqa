"""Strict YAML loader for the shared platform telemetry policy."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

from aiqa_observability.domain import TelemetryPolicy


class _LoggingDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class _TelemetryDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    service_namespace: str
    logging: _LoggingDocument


def load_telemetry_policy(path: Path) -> TelemetryPolicy:
    """Load the versioned policy shared by all Python application processes."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    parsed = _TelemetryDocument.model_validate(document)
    return TelemetryPolicy(
        schema_version=parsed.schema_version,
        service_namespace=parsed.service_namespace,
        log_level=parsed.logging.level,
    )
