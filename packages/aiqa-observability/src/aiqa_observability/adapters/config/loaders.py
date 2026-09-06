"""Shared telemetry policy configuration loading functions."""

from pathlib import Path

from aiqa_observability.adapters.config.documents import TelemetryPolicyDocument
from aiqa_observability.adapters.config.yaml import load_yaml_mapping
from aiqa_observability.domain import TelemetryPolicy


def load_telemetry_policy(path: Path) -> TelemetryPolicy:
    """Load the versioned policy shared by every Python application process."""
    return TelemetryPolicyDocument.model_validate(load_yaml_mapping(path)).to_domain()
