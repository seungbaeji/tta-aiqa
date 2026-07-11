"""Score and prediction distribution shift checks."""

from __future__ import annotations

from collections.abc import Sequence

from ai_quality.observability.application.build_quality_snapshot import (
    build_quality_snapshot,
)
from ai_quality.observability.domain.prediction_event import PredictionEvent
from ai_quality.qa_strategy.domain.drift_signal import ScoreDistributionComparison


# docs:start compare_score_distribution
def compare_score_distribution(
    baseline_events: Sequence[PredictionEvent],
    current_events: Sequence[PredictionEvent],
) -> ScoreDistributionComparison:
    """Compare score and prediction distribution summaries."""
    baseline = build_quality_snapshot(baseline_events)
    current = build_quality_snapshot(current_events)

    return ScoreDistributionComparison(
        baseline_average_score=baseline.average_score,
        current_average_score=current.average_score,
        average_score_delta=current.average_score - baseline.average_score,
        baseline_high_risk_rate=baseline.high_risk_rate,
        current_high_risk_rate=current.high_risk_rate,
        high_risk_rate_delta=current.high_risk_rate - baseline.high_risk_rate,
    )
# docs:end compare_score_distribution
