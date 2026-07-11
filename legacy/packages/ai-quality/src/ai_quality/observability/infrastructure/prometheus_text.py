"""Prometheus text rendering for quality snapshots."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Protocol

from ai_quality.observability.domain.prediction_event import PredictionEvent
from ai_quality.observability.domain.quality_snapshot import QualitySnapshot

SCORE_BUCKETS = (
    (0.0, 0.2),
    (0.2, 0.4),
    (0.4, 0.6),
    (0.6, 0.8),
    (0.8, 1.0),
)


class InputHistogramComparison(Protocol):
    """Input histogram comparison values needed for Prometheus rendering."""

    feature: str
    histogram_bins: Sequence[str]
    baseline_histogram: Sequence[int]
    current_histogram: Sequence[int]


def render_prometheus_metrics(
    snapshot: QualitySnapshot,
    events: Sequence[PredictionEvent] | None = None,
) -> str:
    """Render snapshot as Prometheus text exposition."""
    lines = [
        "# TYPE ai_quality_request_total counter",
        f"ai_quality_request_total {snapshot.request_count}",
        "# TYPE ai_quality_error_total counter",
        f"ai_quality_error_total {snapshot.error_count}",
        "# TYPE ai_quality_validation_failure_total counter",
        f"ai_quality_validation_failure_total {snapshot.validation_failure_count}",
        "# TYPE ai_quality_latency_average_ms gauge",
        f"ai_quality_latency_average_ms {snapshot.average_latency_ms:.3f}",
        "# TYPE ai_quality_score_average gauge",
        f"ai_quality_score_average {snapshot.average_score:.6f}",
        "# TYPE ai_quality_high_risk_rate gauge",
        f"ai_quality_high_risk_rate {snapshot.high_risk_rate:.6f}",
        "# TYPE ai_quality_valid_request_total counter",
        f"ai_quality_valid_request_total {snapshot.valid_request_count}",
        "# TYPE ai_quality_valid_score_average gauge",
        f"ai_quality_valid_score_average {snapshot.valid_average_score:.6f}",
        "# TYPE ai_quality_valid_high_risk_rate gauge",
        f"ai_quality_valid_high_risk_rate {snapshot.valid_high_risk_rate:.6f}",
        "# TYPE ai_quality_prediction_count gauge",
        (
            'ai_quality_prediction_count{prediction="high_risk",scope="all"} '
            f"{snapshot.high_risk_count}"
        ),
        (
            'ai_quality_prediction_count{prediction="low_risk",scope="all"} '
            f"{snapshot.low_risk_count}"
        ),
        (
            'ai_quality_prediction_count{prediction="high_risk",scope="valid"} '
            f"{snapshot.valid_high_risk_count}"
        ),
        (
            'ai_quality_prediction_count{prediction="low_risk",scope="valid"} '
            f"{snapshot.valid_low_risk_count}"
        ),
    ]
    if events is not None:
        lines.extend(render_score_bucket_metrics(events).splitlines())
    return "\n".join(lines) + "\n"


def render_score_bucket_metrics(events: Sequence[PredictionEvent]) -> str:
    """Render score distribution bucket counts for the current batch."""
    valid_events = [event for event in events if not event.validation_failure]
    lines = ["# TYPE ai_quality_score_bucket_count gauge"]
    for scope, scope_events in (("all", events), ("valid", valid_events)):
        counts = _score_bucket_counts(scope_events)
        for bucket, count in counts.items():
            lines.append(
                f'ai_quality_score_bucket_count{{bucket="{bucket}",'
                f'scope="{scope}"}} {count}'
            )
    return "\n".join(lines) + "\n"


def _score_bucket_counts(
    events: Sequence[PredictionEvent],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for event in events:
        counts[_score_bucket_label(event.score)] += 1
    return {
        f"{lower:.1f}-{upper:.1f}": counts[f"{lower:.1f}-{upper:.1f}"]
        for lower, upper in SCORE_BUCKETS
    }


def _score_bucket_label(score: float) -> str:
    clipped_score = min(max(score, 0.0), 1.0)
    for lower, upper in SCORE_BUCKETS[:-1]:
        if lower <= clipped_score < upper:
            return f"{lower:.1f}-{upper:.1f}"
    last_lower, last_upper = SCORE_BUCKETS[-1]
    return f"{last_lower:.1f}-{last_upper:.1f}"


def render_drift_metrics(
    *,
    feature_mean_deltas: Mapping[str, float],
    average_score_delta: float,
    high_risk_rate_delta: float,
    input_histograms: Sequence[InputHistogramComparison] = (),
) -> str:
    """Render drift candidate metrics as Prometheus text exposition."""
    lines = [
        "# TYPE ai_quality_input_mean_delta gauge",
        *[
            (
                f'ai_quality_input_mean_delta{{feature="{feature}"}} '
                f"{delta:.6f}"
            )
            for feature, delta in sorted(feature_mean_deltas.items())
        ],
        "# TYPE ai_quality_score_average_delta gauge",
        f"ai_quality_score_average_delta {average_score_delta:.6f}",
        "# TYPE ai_quality_high_risk_rate_delta gauge",
        f"ai_quality_high_risk_rate_delta {high_risk_rate_delta:.6f}",
    ]
    if input_histograms:
        lines.extend(render_input_histogram_metrics(input_histograms).splitlines())
    return "\n".join(lines) + "\n"


def render_input_histogram_metrics(
    comparisons: Sequence[InputHistogramComparison],
) -> str:
    """Render baseline/current input histogram bucket counts."""
    lines = ["# TYPE ai_quality_input_histogram_count gauge"]
    for comparison in comparisons:
        for bucket, baseline_count, current_count in zip(
            comparison.histogram_bins,
            comparison.baseline_histogram,
            comparison.current_histogram,
            strict=False,
        ):
            lines.append(
                f'ai_quality_input_histogram_count{{feature="{comparison.feature}",'
                f'bucket="{bucket}",scope="baseline"}} {baseline_count}'
            )
            lines.append(
                f'ai_quality_input_histogram_count{{feature="{comparison.feature}",'
                f'bucket="{bucket}",scope="current"}} {current_count}'
            )
    return "\n".join(lines) + "\n"
