"""Shared model and dataset contracts."""

from __future__ import annotations

from typing import TypeAlias

ScalarValue: TypeAlias = str | int | float | bool | None
PredictionEvent: TypeAlias = dict[str, ScalarValue | dict[str, ScalarValue]]

FEATURE_COLUMNS: tuple[str, ...] = (
    "heart_rate",
    "respiratory_rate",
    "body_temperature",
    "oxygen_saturation",
    "systolic_blood_pressure",
    "diastolic_blood_pressure",
)
TARGET_COLUMN = "label"
POSITIVE_LABEL = "high_risk"
NEGATIVE_LABEL = "low_risk"
DEFAULT_THRESHOLD = 0.5
