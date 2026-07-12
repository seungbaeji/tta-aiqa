"""Risk API observability mapping built on the shared platform SDK."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from aiqa_observability import MetricKind, MetricSpec, Telemetry
from aiqa_serving.domain import PredictionEvent

from risk_api.config import RiskApiObservabilityConfig


class RiskApiTelemetry:
    """Own Risk API metric semantics without leaking them into the platform SDK."""

    def __init__(
        self, platform: Telemetry, config: RiskApiObservabilityConfig
    ) -> None:
        self._platform = platform
        self._config = config
        names = config.metrics
        self._requests = platform.counter(
            MetricSpec(
                name=names.request_count,
                description="Risk API HTTP requests",
                kind=MetricKind.COUNTER,
                labels=config.request_metric_labels,
            )
        )
        self._latency = platform.histogram(
            MetricSpec(
                name=names.request_latency,
                description="Risk API HTTP request duration",
                kind=MetricKind.HISTOGRAM,
                labels=config.request_metric_labels,
                buckets=config.buckets.request_latency,
            )
        )
        self._predictions = platform.counter(
            MetricSpec(
                name=names.prediction_count,
                description="Mortality risk predictions",
                kind=MetricKind.COUNTER,
                labels=config.prediction_metric_labels,
            )
        )
        self._scores = platform.histogram(
            MetricSpec(
                name=names.score,
                description="Predicted mortality risk score",
                kind=MetricKind.HISTOGRAM,
                labels=config.prediction_metric_labels,
                buckets=config.buckets.score,
            )
        )
        self._missing = platform.histogram(
            MetricSpec(
                name=names.missing_features,
                description="Missing model input feature count",
                kind=MetricKind.HISTOGRAM,
                labels=config.prediction_metric_labels,
                buckets=config.buckets.missing_features,
            )
        )

    @property
    def platform(self) -> Telemetry:
        """Expose the shared platform for app lifecycle wiring."""
        return self._platform

    @contextmanager
    def request_scope(self, *, request_id: str, scenario: str) -> Iterator[str]:
        """Bind one normalized request context around a FastAPI request."""
        normalized_scenario = self.normalize_scenario(scenario)
        with self._platform.request_scope(
            request_id=request_id,
            scenario=normalized_scenario,
        ):
            yield normalized_scenario

    @contextmanager
    def prediction_scope(self) -> Iterator[None]:
        """Create the prediction child span under the active HTTP request span."""
        with self._platform.operation_scope("risk.predict"):
            yield

    def normalize_scenario(self, scenario: str) -> str:
        """Map caller-controlled scenario values to a bounded metric dimension."""
        if scenario in self._config.allowed_scenarios:
            return scenario
        return self._config.fallback_scenario

    def normalize_route(self, route: str | None) -> str:
        """Prevent unmatched request paths from becoming unbounded metric labels."""
        return route or self._config.unmatched_route

    def normalize_method(self, method: str) -> str:
        """Map caller-controlled HTTP methods to a bounded metric dimension."""
        if method in self._config.allowed_methods:
            return method
        return self._config.fallback_method

    def observe_request(
        self,
        *,
        route: str,
        method: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        """Record one bounded HTTP metric set and correlated structured event."""
        labels = self._request_labels(
            route,
            self.normalize_method(method),
            status_code,
        )
        self._requests.increment(labels=labels)
        self._latency.observe(duration_seconds, labels=labels)
        self._platform.event(
            "http.request.completed",
            attributes={
                "duration_seconds": round(duration_seconds, 6),
                "method": method,
                "route": route,
                "status_code": status_code,
            },
        )

    def record_prediction(self, event: PredictionEvent) -> None:
        """Record a serving event through bounded metrics, log, and current span."""
        scenario = self.normalize_scenario(event.scenario)
        labels = self._prediction_labels(event, scenario)
        self._predictions.increment(labels=labels)
        self._scores.observe(event.score, labels=labels)
        self._missing.observe(float(event.missing_feature_count), labels=labels)
        self._platform.event(
            "risk.prediction.completed",
            attributes={
                "missing_feature_count": event.missing_feature_count,
                "model_profile": event.model_profile,
                "model_version": event.model_version,
                "prediction": event.prediction,
                "score": event.score,
                "threshold": event.threshold,
            },
        )

    def render_metrics(self) -> bytes:
        """Render the Risk API's Prometheus endpoint."""
        return self._platform.render_metrics()

    def shutdown(self) -> None:
        """Flush platform telemetry when the FastAPI process stops."""
        self._platform.shutdown()

    @staticmethod
    def clock() -> float:
        """Return a monotonic clock suitable for request duration measurements."""
        return time.perf_counter()

    def _request_labels(
        self, route: str, method: str, status_code: int
    ) -> dict[str, str]:
        return {
            "service_name": self._platform.resource.service_name,
            "environment": self._platform.resource.environment,
            "route": route,
            "method": method,
            "status_code": str(status_code),
        }

    def _prediction_labels(
        self, event: PredictionEvent, scenario: str
    ) -> dict[str, str]:
        return {
            "service_name": self._platform.resource.service_name,
            "environment": self._platform.resource.environment,
            "model_profile": event.model_profile,
            "model_version": event.model_version,
            "scenario": scenario,
            "prediction": event.prediction,
        }


class PredictionTelemetryRecorder:
    """Serving event recorder adapter backed by Risk API telemetry semantics."""

    def __init__(self, telemetry: RiskApiTelemetry) -> None:
        self._telemetry = telemetry

    def record(self, event: PredictionEvent) -> None:
        """Record one successful prediction event."""
        self._telemetry.record_prediction(event)
