"""Operational quality snapshot domain object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualitySnapshot:
    """Aggregated operational quality signals."""

    request_count: int
    error_count: int
    validation_failure_count: int
    average_latency_ms: float
    high_risk_count: int
    low_risk_count: int
    average_score: float
    valid_request_count: int = 0
    valid_high_risk_count: int = 0
    valid_low_risk_count: int = 0
    valid_average_score: float = 0.0

    @property
    def error_rate(self) -> float:
        """Return error ratio."""
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count

    @property
    def high_risk_rate(self) -> float:
        """Return high_risk prediction ratio."""
        total_predictions = self.high_risk_count + self.low_risk_count
        if total_predictions == 0:
            return 0.0
        return self.high_risk_count / total_predictions

    @property
    def valid_high_risk_rate(self) -> float:
        """Return high_risk ratio among non-validation-failed requests."""
        total_predictions = self.valid_high_risk_count + self.valid_low_risk_count
        if total_predictions == 0:
            return 0.0
        return self.valid_high_risk_count / total_predictions
