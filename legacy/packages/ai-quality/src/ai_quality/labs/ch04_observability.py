"""Shared helpers for chapter 4 observability labs."""

from __future__ import annotations

from pathlib import Path

from ai_quality.common.paths import artifact_path
from ai_quality.observability.domain.prediction_event import PredictionEvent
from ai_quality.observability.infrastructure.jsonl_event_store import (
    read_events_jsonl,
)


def normal_log_path() -> Path:
    """Return normal event log path."""
    return artifact_path("logs", "chapter_04_normal_events.jsonl")


def anomaly_log_path() -> Path:
    """Return anomaly event log path."""
    return artifact_path("logs", "chapter_04_anomaly_events.jsonl")


def require_events(path: Path) -> list[PredictionEvent]:
    """Read events or raise a helpful message."""
    if not path.exists():
        msg = (
            f"Log file not found: {path}\n"
            "Run: uv run python "
            "labs/ch04_observability/build_observability_artifacts.py"
        )
        raise FileNotFoundError(msg)
    return read_events_jsonl(path)
