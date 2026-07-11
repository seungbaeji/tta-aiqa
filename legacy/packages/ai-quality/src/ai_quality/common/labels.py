"""Shared label constants and normalization helpers."""

from __future__ import annotations

from math import isnan
from typing import Final

POSITIVE_LABEL: Final[str] = "high_risk"
NEGATIVE_LABEL: Final[str] = "low_risk"
TARGET_COLUMN: Final[str] = "label"

LABEL_MAP: Final[dict[str, str]] = {
    "High Risk": POSITIVE_LABEL,
    "Low Risk": NEGATIVE_LABEL,
    POSITIVE_LABEL: POSITIVE_LABEL,
    NEGATIVE_LABEL: NEGATIVE_LABEL,
}

ALLOWED_LABELS: Final[set[str]] = {POSITIVE_LABEL, NEGATIVE_LABEL}


def normalize_label(value: object) -> str | None:
    """Return the training label used by the course examples."""
    if value is None:
        return None
    if isinstance(value, float) and isnan(value):
        return None

    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "<na>"}:
        return None
    return LABEL_MAP.get(text, text)


def is_allowed_label(value: object) -> bool:
    """Return whether a value is allowed for binary classification labs."""
    normalized = normalize_label(value)
    return normalized in ALLOWED_LABELS
