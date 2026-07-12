"""YAML loading boundary for model configuration adapters."""

from pathlib import Path
from typing import Any

import yaml


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load a YAML mapping or reject a document with another root type."""
    with path.open(encoding="utf-8") as file:
        payload: Any = yaml.safe_load(file)
    if not isinstance(payload, dict):
        raise ValueError("model configuration root must be a mapping")
    return payload
