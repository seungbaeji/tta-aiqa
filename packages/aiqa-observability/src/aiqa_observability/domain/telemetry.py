"""Framework-neutral contracts for the AIQA observability platform."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Protocol, TypeAlias

TelemetryValue: TypeAlias = str | int | float | bool
TelemetryAttributes: TypeAlias = Mapping[str, TelemetryValue]
MetricLabels: TypeAlias = Mapping[str, str]

_ATTRIBUTE_NAME = re.compile(r"^[a-z][a-z0-9_.]*$")
_METRIC_NAME = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
_METRIC_LABEL = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
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
_FORBIDDEN_METRIC_LABELS = {"request_id", "run_id", "span_id", "trace_id"}


def _attributes_from_mapping(
    attributes: TelemetryAttributes | None,
) -> tuple[tuple[str, TelemetryValue], ...]:
    if attributes is None:
        return ()
    normalized: list[tuple[str, TelemetryValue]] = []
    for name, value in sorted(attributes.items()):
        if not _ATTRIBUTE_NAME.fullmatch(name):
            raise ValueError(f"invalid telemetry attribute name: {name}")
        if name in _RESERVED_ATTRIBUTE_NAMES:
            raise ValueError(f"reserved telemetry attribute name: {name}")
        if isinstance(value, float) and not isfinite(value):
            raise ValueError(f"telemetry attribute must be finite: {name}")
        if not isinstance(value, str | int | float | bool):
            raise ValueError(f"invalid telemetry attribute value: {name}")
        normalized.append((name, value))
    return tuple(normalized)


@dataclass(frozen=True)
class TelemetryPolicy:
    """Versioned policy shared by every AIQA Python process."""

    schema_version: int
    service_namespace: str
    log_level: str

    def __post_init__(self) -> None:
        if self.schema_version < 1:
            raise ValueError("telemetry schema version must be positive")
        if not self.service_namespace:
            raise ValueError("telemetry service namespace is required")
        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            raise ValueError("telemetry log level is invalid")


@dataclass(frozen=True)
class TelemetryResource:
    """Process-lifetime identity carried by every emitted signal."""

    service_name: str
    service_namespace: str
    environment: str

    def __post_init__(self) -> None:
        if not self.service_name or not self.service_namespace or not self.environment:
            raise ValueError("telemetry resource identity is required")

    def as_log_fields(self) -> dict[str, str]:
        """Return the stable structured-log representation of this resource."""
        return {
            "service_name": self.service_name,
            "service_namespace": self.service_namespace,
            "environment": self.environment,
        }

    def as_trace_attributes(self) -> dict[str, str]:
        """Return OpenTelemetry resource attributes for this process."""
        return {
            "service.name": self.service_name,
            "service.namespace": self.service_namespace,
            "deployment.environment.name": self.environment,
        }


@dataclass(frozen=True)
class TelemetryContext:
    """Execution-local correlation values independent of a web framework."""

    operation: str
    request_id: str | None = None
    run_id: str | None = None
    scenario: str | None = None
    attributes: tuple[tuple[str, TelemetryValue], ...] = ()

    def __post_init__(self) -> None:
        if not self.operation:
            raise ValueError("telemetry operation is required")
        if self.request_id is not None and not self.request_id:
            raise ValueError("request ID cannot be empty")
        if self.run_id is not None and not self.run_id:
            raise ValueError("run ID cannot be empty")
        if self.scenario is not None and not self.scenario:
            raise ValueError("scenario cannot be empty")
        names = [name for name, _ in self.attributes]
        if len(names) != len(set(names)):
            raise ValueError("telemetry context attributes must be unique")

    @classmethod
    def create(
        cls,
        *,
        operation: str,
        request_id: str | None = None,
        run_id: str | None = None,
        scenario: str | None = None,
        attributes: TelemetryAttributes | None = None,
    ) -> TelemetryContext:
        """Create an immutable context from a boundary mapping."""
        return cls(
            operation=operation,
            request_id=request_id,
            run_id=run_id,
            scenario=scenario,
            attributes=_attributes_from_mapping(attributes),
        )

    def as_log_fields(self) -> dict[str, TelemetryValue]:
        """Return fields safe to attach to structured logs and trace spans."""
        fields: dict[str, TelemetryValue] = {"operation": self.operation}
        if self.request_id is not None:
            fields["request_id"] = self.request_id
        if self.run_id is not None:
            fields["run_id"] = self.run_id
        if self.scenario is not None:
            fields["scenario"] = self.scenario
        fields.update(self.attributes)
        return fields


@dataclass(frozen=True)
class TelemetryEvent:
    """A named, structured occurrence emitted by an application process."""

    name: str
    attributes: tuple[tuple[str, TelemetryValue], ...] = ()

    def __post_init__(self) -> None:
        if not _ATTRIBUTE_NAME.fullmatch(self.name):
            raise ValueError(f"invalid telemetry event name: {self.name}")
        names = [name for name, _ in self.attributes]
        if len(names) != len(set(names)):
            raise ValueError("telemetry event attributes must be unique")

    @classmethod
    def create(
        cls, name: str, attributes: TelemetryAttributes | None = None
    ) -> TelemetryEvent:
        """Create an immutable event from a boundary mapping."""
        return cls(name=name, attributes=_attributes_from_mapping(attributes))

    def as_fields(self) -> dict[str, TelemetryValue]:
        """Return event fields for logging and span event attributes."""
        return dict(self.attributes)


class MetricKind(StrEnum):
    """Prometheus metric kinds supported by the platform SDK."""

    COUNTER = "counter"
    HISTOGRAM = "histogram"


@dataclass(frozen=True)
class MetricSpec:
    """A bounded metric declaration owned by an application."""

    name: str
    description: str
    kind: MetricKind
    labels: tuple[str, ...]
    buckets: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        if not self.name or not self.description:
            raise ValueError("metric name and description are required")
        if not _METRIC_NAME.fullmatch(self.name):
            raise ValueError(f"invalid Prometheus metric name: {self.name}")
        if not self.labels or len(self.labels) != len(set(self.labels)):
            raise ValueError("metric labels must be non-empty and unique")
        invalid_labels = [
            label
            for label in self.labels
            if not _METRIC_LABEL.fullmatch(label) or label.startswith("__")
        ]
        if invalid_labels:
            raise ValueError(f"invalid Prometheus metric labels: {invalid_labels}")
        forbidden = _FORBIDDEN_METRIC_LABELS & set(self.labels)
        if forbidden:
            raise ValueError(f"forbidden metric labels: {sorted(forbidden)}")
        if self.kind is MetricKind.HISTOGRAM:
            if "le" in self.labels:
                raise ValueError("histogram metric labels cannot include le")
            if not self.buckets or tuple(sorted(self.buckets)) != self.buckets:
                raise ValueError("histogram buckets must be non-empty and sorted")
            if len(self.buckets) != len(set(self.buckets)):
                raise ValueError("histogram buckets must be unique")
        elif self.buckets:
            raise ValueError("only histograms can define buckets")


class CounterMetric(Protocol):
    """Application-facing bounded counter handle."""

    def increment(self, *, labels: MetricLabels, amount: float = 1.0) -> None:
        """Increase the counter using exactly its declared label set."""


class HistogramMetric(Protocol):
    """Application-facing bounded histogram handle."""

    def observe(self, value: float, *, labels: MetricLabels) -> None:
        """Observe one finite value using exactly its declared label set."""
