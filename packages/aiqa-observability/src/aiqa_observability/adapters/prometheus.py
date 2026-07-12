"""Prometheus client implementation for explicitly declared application metrics."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

from aiqa_observability.domain import MetricKind, MetricSpec


class PrometheusMeter:
    """Create metrics only from bounded, application-owned specifications."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self._names: set[str] = set()

    def counter(self, spec: MetricSpec) -> Counter:
        """Register one counter in this process-local registry."""
        self._validate(spec, MetricKind.COUNTER)
        metric = Counter(
            spec.name,
            spec.description,
            spec.labels,
            registry=self.registry,
        )
        self._names.add(spec.name)
        return metric

    def histogram(self, spec: MetricSpec) -> Histogram:
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
        return metric

    def render(self) -> bytes:
        """Render this process's Prometheus exposition."""
        return generate_latest(self.registry)

    def _validate(self, spec: MetricSpec, expected_kind: MetricKind) -> None:
        if spec.kind is not expected_kind:
            raise ValueError(f"metric {spec.name} has invalid kind")
        if spec.name in self._names:
            raise ValueError(f"metric is already registered: {spec.name}")
