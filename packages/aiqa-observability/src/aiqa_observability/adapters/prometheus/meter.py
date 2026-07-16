"""Prometheus client registry implementation for declared application metrics."""

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

from aiqa_observability.adapters.prometheus.contracts import (
    validate_metric_registration,
)
from aiqa_observability.adapters.prometheus.handles import (
    PrometheusCounter,
    PrometheusHistogram,
)
from aiqa_observability.domain import (
    CounterMetric,
    HistogramMetric,
    MetricKind,
    MetricSpec,
)


class PrometheusMeter:
    """Create metrics only from bounded, application-owned specifications."""

    def __init__(self) -> None:
        """Create a private Prometheus registry for one application process."""
        self.registry = CollectorRegistry()
        self._names: set[str] = set()

    def counter(self, spec: MetricSpec) -> CounterMetric:
        """Register one counter in this process-local registry."""
        validate_metric_registration(spec, MetricKind.COUNTER, self._names)
        metric = Counter(
            spec.name,
            spec.description,
            spec.labels,
            registry=self.registry,
        )
        self._names.add(spec.name)
        return PrometheusCounter(metric, spec.labels)

    def histogram(self, spec: MetricSpec) -> HistogramMetric:
        """Register one histogram in this process-local registry."""
        validate_metric_registration(spec, MetricKind.HISTOGRAM, self._names)
        metric = Histogram(
            spec.name,
            spec.description,
            spec.labels,
            buckets=spec.buckets,
            registry=self.registry,
        )
        self._names.add(spec.name)
        return PrometheusHistogram(metric, spec.labels)

    def render(self) -> bytes:
        """Render this process's Prometheus exposition."""
        return generate_latest(self.registry)
