"""Drift signal domain objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureDistributionComparison:
    """Comparison for one numeric input feature."""

    feature: str
    baseline_mean: float
    current_mean: float
    mean_delta: float
    mean_delta_ratio: float
    histogram_bins: tuple[str, ...] = ()
    baseline_histogram: tuple[int, ...] = ()
    current_histogram: tuple[int, ...] = ()

    @property
    def shifted(self) -> bool:
        """Return whether the feature mean changed enough to review."""
        return abs(self.mean_delta_ratio) >= 0.1 or self.histogram_distance >= 0.25

    @property
    def histogram_distance(self) -> float:
        """Return normalized histogram distance between baseline and current."""
        baseline_total = sum(self.baseline_histogram)
        current_total = sum(self.current_histogram)
        if baseline_total == 0 or current_total == 0:
            return 0.0

        distance = 0.0
        for baseline_count, current_count in zip(
            self.baseline_histogram,
            self.current_histogram,
            strict=False,
        ):
            baseline_ratio = baseline_count / baseline_total
            current_ratio = current_count / current_total
            distance += abs(baseline_ratio - current_ratio)
        return distance / 2


@dataclass(frozen=True)
class ScoreDistributionComparison:
    """Comparison of score distribution summary."""

    baseline_average_score: float
    current_average_score: float
    average_score_delta: float
    baseline_high_risk_rate: float
    current_high_risk_rate: float
    high_risk_rate_delta: float
