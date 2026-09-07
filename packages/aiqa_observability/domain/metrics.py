"""Bounded Prometheus metric declarations and application-facing handles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Protocol

from aiqa_observability.domain.attributes import MetricLabels

_METRIC_NAME = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
_METRIC_LABEL = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_FORBIDDEN_METRIC_LABELS = {"request_id", "run_id", "span_id", "trace_id"}


class MetricKind(StrEnum):
    """Prometheus metric kinds supported by the platform SDK."""

    COUNTER = "counter"
    HISTOGRAM = "histogram"


@dataclass(frozen=True)
class MetricSpec:
    """Bounded metric declaration owned by one application."""

    name: str
    description: str
    kind: MetricKind
    labels: tuple[str, ...]
    buckets: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.name, str)
            or not self.name
            or not isinstance(self.description, str)
            or not self.description
        ):
            raise ValueError("metric name and description are required")
        if not isinstance(self.kind, MetricKind):
            raise ValueError("metric kind must be a MetricKind")
        if not _METRIC_NAME.fullmatch(self.name):
            raise ValueError(f"invalid Prometheus metric name: {self.name}")
        if not isinstance(self.labels, tuple) or not self.labels:
            raise ValueError("metric labels must be a non-empty tuple")
        if len(self.labels) != len(set(self.labels)):
            raise ValueError("metric labels must be unique")
        invalid_labels = [
            label
            for label in self.labels
            if not isinstance(label, str)
            or not _METRIC_LABEL.fullmatch(label)
            or label.startswith("__")
        ]
        if invalid_labels:
            raise ValueError(f"invalid Prometheus metric labels: {invalid_labels}")
        forbidden = _FORBIDDEN_METRIC_LABELS & set(self.labels)
        if forbidden:
            raise ValueError(f"forbidden metric labels: {sorted(forbidden)}")
        validate_metric_buckets(self.kind, self.labels, self.buckets)


def validate_metric_buckets(
    kind: MetricKind,
    labels: tuple[str, ...],
    buckets: tuple[float, ...],
) -> None:
    """Validate histogram-only finite bucket declarations."""
    if kind is MetricKind.HISTOGRAM:
        if "le" in labels:
            raise ValueError("histogram metric labels cannot include le")
        if not isinstance(buckets, tuple) or not buckets:
            raise ValueError("histogram buckets must be a non-empty tuple")
        if any(
            isinstance(bucket, bool)
            or not isinstance(bucket, (int, float))
            or not isfinite(bucket)
            for bucket in buckets
        ):
            raise ValueError("histogram buckets must be finite numbers")
        if tuple(sorted(buckets)) != buckets:
            raise ValueError("histogram buckets must be sorted")
        if len(buckets) != len(set(buckets)):
            raise ValueError("histogram buckets must be unique")
    elif buckets:
        raise ValueError("only histograms can define buckets")


class CounterMetric(Protocol):
    """Application-facing bounded counter handle."""

    def increment(self, *, labels: MetricLabels, amount: float = 1.0) -> None:
        """Increase the counter using exactly its declared label set."""
        ...


class HistogramMetric(Protocol):
    """Application-facing bounded histogram handle."""

    def observe(self, value: float, *, labels: MetricLabels) -> None:
        """Observe one finite value using exactly its declared label set."""
        ...
