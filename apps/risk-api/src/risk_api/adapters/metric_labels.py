"""Bounded Prometheus label mapping for Risk API telemetry semantics."""

from aiqa_observability import TelemetryResource
from aiqa_serving.domain import PredictionEvent


def request_metric_labels(
    resource: TelemetryResource,
    *,
    route: str,
    method: str,
    status_code: int,
) -> dict[str, str]:
    """Return the stable label set for one completed Risk API HTTP request."""
    return {
        "service_name": resource.service_name,
        "environment": resource.environment,
        "route": route,
        "method": method,
        "status_code": str(status_code),
    }


def prediction_metric_labels(
    resource: TelemetryResource,
    *,
    event: PredictionEvent,
    scenario: str,
) -> dict[str, str]:
    """Return the stable label set for one completed mortality-risk prediction."""
    return {
        "service_name": resource.service_name,
        "environment": resource.environment,
        "model_profile": event.model_profile,
        "model_version": event.model_version,
        "scenario": scenario,
        "prediction": event.prediction,
    }
