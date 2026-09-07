"""Framework-neutral telemetry attribute and metric-label contracts."""

from __future__ import annotations

import re
from collections.abc import Mapping
from math import isfinite
from typing import TypeAlias

TelemetryValue: TypeAlias = str | int | float | bool
TelemetryAttributes: TypeAlias = Mapping[str, TelemetryValue]
MetricLabels: TypeAlias = Mapping[str, str]

_ATTRIBUTE_NAME = re.compile(r"^[a-z][a-z0-9_.]*$")
_RESERVED_ATTRIBUTE_NAMES = {
    "environment",
    "event",
    "level",
    "message",
    "operation",
    "request_id",
    "run_id",
    "scenario",
    "service_name",
    "service_namespace",
    "span_id",
    "timestamp",
    "trace_id",
}


def normalize_telemetry_attributes(
    attributes: TelemetryAttributes | None,
) -> tuple[tuple[str, TelemetryValue], ...]:
    """Validate a boundary mapping and return deterministic immutable attributes."""
    if attributes is None:
        return ()
    normalized = tuple(sorted(attributes.items()))
    validate_telemetry_attribute_pairs(normalized)
    return normalized


def validate_telemetry_attribute_pairs(
    attributes: tuple[tuple[str, TelemetryValue], ...],
) -> None:
    """Validate immutable telemetry attributes before they enter context or events."""
    if not isinstance(attributes, tuple):
        raise ValueError("telemetry attributes must be an immutable tuple")
    names: list[str] = []
    for item in attributes:
        if not isinstance(item, tuple) or len(item) != 2:
            raise ValueError("telemetry attributes must contain name-value pairs")
        name, value = item
        validate_telemetry_attribute_name(name)
        if isinstance(value, float) and not isfinite(value):
            raise ValueError(f"telemetry attribute must be finite: {name}")
        if not isinstance(value, str | int | float | bool):
            raise ValueError(f"invalid telemetry attribute value: {name}")
        names.append(name)
    if len(names) != len(set(names)):
        raise ValueError("telemetry attributes must be unique")
    if tuple(names) != tuple(sorted(names)):
        raise ValueError("telemetry attributes must be sorted")


def validate_telemetry_attribute_name(name: object) -> None:
    """Validate one non-reserved telemetry attribute field name."""
    if not isinstance(name, str) or not _ATTRIBUTE_NAME.fullmatch(name):
        raise ValueError(f"invalid telemetry attribute name: {name}")
    if name in _RESERVED_ATTRIBUTE_NAMES:
        raise ValueError(f"reserved telemetry attribute name: {name}")


def validate_telemetry_event_name(name: object) -> None:
    """Validate one dot-separated telemetry event name."""
    if not isinstance(name, str) or not _ATTRIBUTE_NAME.fullmatch(name):
        raise ValueError(f"invalid telemetry event name: {name}")
