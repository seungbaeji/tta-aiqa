"""Trace likely quality issue candidates from observed signals."""

from __future__ import annotations

from collections.abc import Sequence

from ai_quality.observability.application.analyze_quality_signal import (
    QualitySignalReport,
)
from ai_quality.observability.domain.prediction_event import PredictionEvent
from ai_quality.qa_strategy.domain.drift_signal import (
    FeatureDistributionComparison,
    ScoreDistributionComparison,
)
from ai_quality.qa_strategy.domain.quality_issue import IssueCandidate, IssueTraceReport


def _validation_audit_reference(events: Sequence[PredictionEvent] | None) -> str:
    """Return one request-level reference for validation failures."""
    if not events:
        return "artifacts/reports/chapter_04_validation_failure_examples.md"

    for event in events:
        if event.validation_failure:
            parts = [
                f"request_id={event.request_id}",
                f"client_id={event.client_id or '-'}",
                f"source_system={event.source_system or '-'}",
                f"failed_field={event.failed_field or '-'}",
            ]
            return ", ".join(parts)

    return "artifacts/reports/chapter_04_validation_failure_examples.md"


# docs:start trace_quality_issue
def trace_quality_issue(
    feature_comparisons: list[FeatureDistributionComparison],
    score_comparison: ScoreDistributionComparison,
    quality_report: QualitySignalReport,
    current_events: Sequence[PredictionEvent] | None = None,
) -> IssueTraceReport:
    """Create QA-oriented cause candidates from data, score, and ops signals."""
    candidates: list[IssueCandidate] = []
    shifted_features = [item.feature for item in feature_comparisons if item.shifted]

    if shifted_features:
        candidates.append(
            IssueCandidate(
                category="input_case_mix_shift",
                evidence=f"shifted_features={', '.join(shifted_features)}",
                owner="Data Engineering",
                audit_reference="artifacts/reports/drift_report.md#input-distribution",
                next_action="최근 입력 출처와 전처리 변경을 확인합니다.",
            )
        )
    if score_comparison.high_risk_rate_delta > 0.15:
        candidates.append(
            IssueCandidate(
                category="prediction_shift",
                evidence=(
                    "high_risk_rate_delta="
                    f"{score_comparison.high_risk_rate_delta:.4f}"
                ),
                owner="ML Engineering",
                audit_reference=(
                    "artifacts/reports/drift_report.md"
                    "#score-and-prediction-distribution"
                ),
                next_action="점수 분포와 임계값 설정을 비교합니다.",
            )
        )
    if quality_report.error_rate_delta > 0.03:
        audit_reference = _validation_audit_reference(current_events)
        candidates.append(
            IssueCandidate(
                category="api_validation",
                evidence=f"error_rate_delta={quality_report.error_rate_delta:.4f}",
                owner="Client Integration",
                audit_reference=audit_reference,
                next_action=(
                    "검증 실패 예시에서 failed_field, client_id, source_system을 "
                    "확인하고 Client Integration owner에게 전달합니다."
                ),
            )
        )
    if quality_report.latency_delta_ms > 100:
        candidates.append(
            IssueCandidate(
                category="service_latency",
                evidence=f"latency_delta_ms={quality_report.latency_delta_ms:.1f}",
                owner="Platform/MLOps",
                audit_reference=(
                    "artifacts/grafana/ai_quality_overview_dashboard.json"
                    "#average-latency"
                ),
                next_action="서비스 부하, 의존성 지연, Pod 상태를 확인합니다.",
            )
        )

    return IssueTraceReport(candidates=tuple(candidates))
# docs:end trace_quality_issue
