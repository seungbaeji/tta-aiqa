"""Build quality snapshots from prediction events."""

from __future__ import annotations

from collections.abc import Sequence

from ai_quality.common.labels import NEGATIVE_LABEL, POSITIVE_LABEL
from ai_quality.observability.domain.prediction_event import PredictionEvent
from ai_quality.observability.domain.quality_snapshot import QualitySnapshot


# docs:start build_quality_snapshot
def build_quality_snapshot(
    events: Sequence[PredictionEvent],
) -> QualitySnapshot:
    """Aggregate prediction events into operational quality signals."""
    request_count = len(events)
    valid_events = [event for event in events if not event.validation_failure]
    error_count = sum(1 for event in events if event.status_code >= 400)
    validation_failure_count = sum(1 for event in events if event.validation_failure)
    latency_sum = sum(event.latency_ms for event in events)
    score_sum = sum(event.score for event in events)
    valid_score_sum = sum(event.score for event in valid_events)

    return QualitySnapshot(
        request_count=request_count,
        error_count=error_count,
        validation_failure_count=validation_failure_count,
        average_latency_ms=latency_sum / request_count if request_count else 0.0,
        high_risk_count=sum(
            1 for event in events if event.prediction == POSITIVE_LABEL
        ),
        low_risk_count=sum(
            1 for event in events if event.prediction == NEGATIVE_LABEL
        ),
        average_score=score_sum / request_count if request_count else 0.0,
        valid_request_count=len(valid_events),
        valid_high_risk_count=sum(
            1 for event in valid_events if event.prediction == POSITIVE_LABEL
        ),
        valid_low_risk_count=sum(
            1 for event in valid_events if event.prediction == NEGATIVE_LABEL
        ),
        valid_average_score=(
            valid_score_sum / len(valid_events) if valid_events else 0.0
        ),
    )
# docs:end build_quality_snapshot
