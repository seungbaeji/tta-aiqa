"""Analyze operational quality signal changes."""

from __future__ import annotations

from dataclasses import dataclass

from ai_quality.observability.domain.quality_snapshot import QualitySnapshot


@dataclass(frozen=True)
class QualitySignalReport:
    """Comparison between baseline and current operational quality."""

    error_rate_delta: float
    latency_delta_ms: float
    high_risk_rate_delta: float
    average_score_delta: float
    notes: tuple[str, ...]


def analyze_quality_signal(
    baseline: QualitySnapshot,
    current: QualitySnapshot,
) -> QualitySignalReport:
    """Compare two snapshots and return QA notes."""
    error_rate_delta = current.error_rate - baseline.error_rate
    latency_delta_ms = current.average_latency_ms - baseline.average_latency_ms
    high_risk_rate_delta = current.high_risk_rate - baseline.high_risk_rate
    average_score_delta = current.average_score - baseline.average_score

    notes: list[str] = []
    if error_rate_delta > 0.03:
        notes.append("오류율이 증가했습니다. 검증 실패를 확인합니다.")
    if latency_delta_ms > 100:
        notes.append(
            "지연 시간이 증가했습니다. 서비스 부하나 의존성 지연을 확인합니다."
        )
    if high_risk_rate_delta > 0.15:
        notes.append("예측 분포가 high_risk 쪽으로 이동했습니다.")
    if average_score_delta > 0.10:
        notes.append("점수 분포가 높은 방향으로 이동했습니다.")

    return QualitySignalReport(
        error_rate_delta=error_rate_delta,
        latency_delta_ms=latency_delta_ms,
        high_risk_rate_delta=high_risk_rate_delta,
        average_score_delta=average_score_delta,
        notes=tuple(notes),
    )
