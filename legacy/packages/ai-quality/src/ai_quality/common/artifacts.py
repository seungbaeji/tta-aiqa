"""Artifact path helpers."""

from __future__ import annotations

from pathlib import Path

from ai_quality.common.paths import artifact_path


def ensure_artifact_dir(*parts: str) -> Path:
    """Create and return an artifact directory."""
    path = artifact_path(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path

