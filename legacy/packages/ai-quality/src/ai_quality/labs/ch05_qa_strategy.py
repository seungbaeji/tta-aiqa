"""Shared helpers for chapter 5 labs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ai_quality.common.config import load_yaml
from ai_quality.common.paths import artifact_path, config_path, data_path
from ai_quality.observability.application.generate_sample_events import (
    generate_sample_events,
)
from ai_quality.observability.domain.prediction_event import PredictionEvent
from ai_quality.observability.infrastructure.jsonl_event_store import (
    read_events_jsonl,
)


def load_yaml_config(*parts: str) -> dict[str, Any]:
    """Load one YAML config file."""
    return load_yaml(config_path(*parts))


def load_serving_requests() -> pd.DataFrame:
    """Load holdout-based baseline request rows."""
    return pd.read_csv(data_path("serving_requests_valid.csv"))


def load_current_serving_requests() -> pd.DataFrame:
    """Load current input rows selected from the operational holdout."""
    current_path = data_path("serving_requests_current.csv")
    if current_path.exists():
        return pd.read_csv(current_path)
    return load_serving_requests()


def baseline_events() -> list[PredictionEvent]:
    """Return holdout-based baseline prediction events."""
    event_path = data_path("operational_baseline_events.jsonl")
    if event_path.exists():
        return read_events_jsonl(event_path)
    return generate_sample_events(scenario="normal")


def current_events() -> list[PredictionEvent]:
    """Return current operational incident prediction events."""
    event_path = data_path("operational_current_events.jsonl")
    if event_path.exists():
        return read_events_jsonl(event_path)
    return generate_sample_events(scenario="anomaly")


def report_path(filename: str) -> Path:
    """Return report artifact path."""
    return artifact_path("reports", filename)
