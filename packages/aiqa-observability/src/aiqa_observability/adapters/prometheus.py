"""Prometheus client implementation for explicitly declared application metrics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

from aiqa_observability.domain import (
    CounterMetric,
    HistogramMetric,
    MetricKind,
    MetricLabels,
    MetricSpec,
)


@dataclass(frozen=True)
class _PrometheusCounter:
    metric: Counter
    labels: tuple[str, ...]

    def increment(self, *, labels: MetricLabels, amount: float = 1.0) -> None:
        """Increase one counter after validating its bounded label contract."""
        if not isfinite(amount) or amount < 0:
            raise ValueError("counter increment must be finite and non-negative")
        self.metric.labels(**_validated_labels(labels, self.labels)).inc(amount)


@dataclass(frozen=True)
class _PrometheusHistogram:
    metric: Histogram
    labels: tuple[str, ...]

    def observe(self, value: float, *, labels: MetricLabels) -> None:
        """Observe one histogram value after validating labels and value."""
        if not isfinite(value):
            raise ValueError("histogram observation must be finite")
        self.metric.labels(**_validated_labels(labels, self.labels)).observe(value)


class PrometheusMeter:
    """Create metrics only from bounded, application-owned specifications."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self._names: set[str] = set()

    def counter(self, spec: MetricSpec) -> CounterMetric:
        """Register one counter in this process-local registry."""
        self._validate(spec, MetricKind.COUNTER)
        metric = Counter(
            spec.name,
            spec.description,
            spec.labels,
            registry=self.registry,
        )
        self._names.add(spec.name)
        return _PrometheusCounter(metric, spec.labels)

    def histogram(self, spec: MetricSpec) -> HistogramMetric:
        """Register one histogram in this process-local registry."""
        self._validate(spec, MetricKind.HISTOGRAM)
        metric = Histogram(
            spec.name,
            spec.description,
            spec.labels,
            buckets=spec.buckets,
            registry=self.registry,
        )
        self._names.add(spec.name)
        return _PrometheusHistogram(metric, spec.labels)

    def render(self) -> bytes:
        """Render this process's Prometheus exposition."""
        return generate_latest(self.registry)

    def _validate(self, spec: MetricSpec, expected_kind: MetricKind) -> None:
        if spec.kind is not expected_kind:
            raise ValueError(f"metric {spec.name} has invalid kind")
        if spec.name in self._names:
            raise ValueError(f"metric is already registered: {spec.name}")


def _validated_labels(
    labels: Mapping[str, str], expected: tuple[str, ...]
) -> dict[str, str]:
    actual = dict(labels)
    if set(actual) != set(expected):
        raise ValueError(
            "metric labels do not match declaration: "
            f"expected={sorted(expected)}, actual={sorted(actual)}"
        )
    if any(not isinstance(value, str) for value in actual.values()):
        raise ValueError("metric label values must be strings")
    return actual
