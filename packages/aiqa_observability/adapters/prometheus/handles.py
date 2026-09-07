"""Prometheus counter and histogram handle implementations."""

from dataclasses import dataclass
from math import isfinite

from prometheus_client import Counter, Histogram

from aiqa_observability.adapters.prometheus.contracts import validate_metric_labels
from aiqa_observability.domain import MetricLabels


@dataclass(frozen=True)
class PrometheusCounter:
    """Bounded application counter backed by one Prometheus counter collector."""

    metric: Counter
    labels: tuple[str, ...]

    def increment(self, *, labels: MetricLabels, amount: float = 1.0) -> None:
        """Increase one counter after validating its bounded label contract."""
        if not isfinite(amount) or amount < 0:
            raise ValueError("counter increment must be finite and non-negative")
        self.metric.labels(**validate_metric_labels(labels, self.labels)).inc(amount)


@dataclass(frozen=True)
class PrometheusHistogram:
    """Bounded application histogram backed by one Prometheus histogram collector."""

    metric: Histogram
    labels: tuple[str, ...]

    def observe(self, value: float, *, labels: MetricLabels) -> None:
        """Observe one histogram value after validating labels and value."""
        if not isfinite(value):
            raise ValueError("histogram observation must be finite")
        self.metric.labels(**validate_metric_labels(labels, self.labels)).observe(value)
