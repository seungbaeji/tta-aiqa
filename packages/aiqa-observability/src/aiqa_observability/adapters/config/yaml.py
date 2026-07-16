"""YAML loading boundary for shared telemetry policy documents."""

from pathlib import Path
from typing import Any

import yaml


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load a YAML mapping or reject a document with another root type."""
    payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("telemetry policy root must be a mapping")
    return payload
