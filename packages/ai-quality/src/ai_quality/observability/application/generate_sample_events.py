"""Generate deterministic prediction events for observability labs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ai_quality.common.labels import NEGATIVE_LABEL, POSITIVE_LABEL
from ai_quality.observability.domain.prediction_event import PredictionEvent
from ai_quality.observability.domain.request_context import RequestContext


def generate_sample_events(
    count: int = 120,
    scenario: str = "normal",
) -> list[PredictionEvent]:
    """Generate sample prediction events for one scenario."""
    start = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    events: list[PredictionEvent] = []

    for index in range(count):
        score = build_score(index, scenario)
        status_code = 422 if scenario == "anomaly" and index % 17 == 0 else 200
        validation_failure = status_code >= 400
        latency_ms = build_latency(index, scenario)
        prediction = POSITIVE_LABEL if score >= 0.5 else NEGATIVE_LABEL

        timestamp = (start + timedelta(seconds=index * 5)).isoformat()
        context = RequestContext.create(
            request_id=f"{scenario}-{index:04d}",
            trace_id=f"{scenario}-trace-{index // 3:04d}",
            timestamp=timestamp,
        )

        events.append(
            PredictionEvent(
                timestamp=context.timestamp,
                request_id=context.request_id,
                trace_id=context.trace_id,
                model_version="v1",
                score=score,
                threshold=0.5,
                prediction=prediction,
                latency_ms=latency_ms,
                status_code=status_code,
                validation_failure=validation_failure,
                client_id=build_client_id(scenario, validation_failure),
                source_system=build_source_system(scenario, validation_failure),
                failed_field=build_failed_field(index, validation_failure),
                error_category=(
                    "schema_validation" if validation_failure else None
                ),
                error_detail=build_error_detail(index, validation_failure),
                owner="Client Integration" if validation_failure else None,
            )
        )

    return events


def build_score(index: int, scenario: str) -> float:
    """Return deterministic score for a scenario."""
    if scenario == "anomaly":
        return min(0.99, 0.45 + (index % 10) * 0.055)
    return 0.25 + (index % 10) * 0.05


def build_latency(index: int, scenario: str) -> float:
    """Return deterministic latency for a scenario."""
    base = 180.0 if scenario == "anomaly" else 60.0
    return base + (index % 8) * 12.5


def build_client_id(scenario: str, validation_failure: bool) -> str:
    """Return deterministic client id for an event."""
    if validation_failure:
        return "partner-feed-v2"
    if scenario == "anomaly":
        return "mobile-checkin-v2"
    return "baseline-client-v1"


def build_source_system(scenario: str, validation_failure: bool) -> str:
    """Return deterministic source system for an event."""
    if validation_failure:
        return "upstream-partner-feed"
    if scenario == "anomaly":
        return "mobile-checkin"
    return "training-baseline"


def build_failed_field(index: int, validation_failure: bool) -> str | None:
    """Return representative failed field for validation failures."""
    if not validation_failure:
        return None
    return "oxygen_saturation" if index % 2 == 0 else "heart_rate"


def build_error_detail(index: int, validation_failure: bool) -> str | None:
    """Return representative validation error detail."""
    if not validation_failure:
        return None
    if index % 2 == 0:
        return "oxygen_saturation is outside accepted serving range"
    return "heart_rate is missing from client payload"
