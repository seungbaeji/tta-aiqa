"""Risk API telemetry adapter built on the shared observability platform SDK."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from aiqa_observability import MetricKind, MetricSpec, Telemetry
from aiqa_serving.domain import PredictionEvent

from risk_api.adapters.config import RiskApiObservabilityConfig
from risk_api.adapters.metric_labels import (
    prediction_metric_labels,
    request_metric_labels,
)

RISK_PREDICTION_OPERATION = "risk.predict"
HTTP_REQUEST_COMPLETED_EVENT = "http.request.completed"
RISK_PREDICTION_COMPLETED_EVENT = "risk.prediction.completed"


class RiskApiTelemetry:
    """Own Risk API metric semantics without leaking them into the platform SDK."""

    def __init__(
        self,
        platform: Telemetry,
        config: RiskApiObservabilityConfig,
    ) -> None:
        """Register the application-owned metric instruments on one platform facade."""
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
        with self._platform.operation_scope(RISK_PREDICTION_OPERATION):
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
        labels = request_metric_labels(
            self._platform.resource,
            route=route,
            method=self.normalize_method(method),
            status_code=status_code,
        )
        self._requests.increment(labels=labels)
        self._latency.observe(duration_seconds, labels=labels)
        self._platform.event(
            HTTP_REQUEST_COMPLETED_EVENT,
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
        labels = prediction_metric_labels(
            self._platform.resource,
            event=event,
            scenario=scenario,
        )
        self._predictions.increment(labels=labels)
        self._scores.observe(event.score, labels=labels)
        self._missing.observe(float(event.missing_feature_count), labels=labels)
        self._platform.event(
            RISK_PREDICTION_COMPLETED_EVENT,
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


class PredictionTelemetryRecorder:
    """Serving event recorder adapter backed by Risk API telemetry semantics."""

    def __init__(self, telemetry: RiskApiTelemetry) -> None:
        """Bind one application telemetry adapter to the serving event port."""
        self._telemetry = telemetry

    def record(self, event: PredictionEvent) -> None:
        """Record one successful prediction event."""
        self._telemetry.record_prediction(event)
