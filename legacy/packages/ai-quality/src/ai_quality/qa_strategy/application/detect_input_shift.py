"""Input distribution shift checks."""

from __future__ import annotations

import pandas as pd

from ai_quality.qa_strategy.domain.drift_signal import (
    FeatureDistributionComparison,
)


# docs:start compare_input_distribution
def compare_input_distribution(
    baseline: pd.DataFrame,
    current: pd.DataFrame,
    feature_columns: list[str],
    bin_count: int = 5,
) -> list[FeatureDistributionComparison]:
    """Compare feature means and histogram summaries between input datasets."""
    comparisons: list[FeatureDistributionComparison] = []

    for feature in feature_columns:
        baseline_values = _numeric_values(baseline, feature)
        current_values = _numeric_values(current, feature)
        baseline_mean = _mean(baseline_values)
        current_mean = _mean(current_values)
        denominator = abs(baseline_mean) if baseline_mean != 0 else 1.0
        mean_delta = current_mean - baseline_mean
        edges = _histogram_edges([*baseline_values, *current_values], bin_count)
        comparisons.append(
            FeatureDistributionComparison(
                feature=feature,
                baseline_mean=baseline_mean,
                current_mean=current_mean,
                mean_delta=mean_delta,
                mean_delta_ratio=mean_delta / denominator,
                histogram_bins=_histogram_labels(edges),
                baseline_histogram=_histogram_counts(baseline_values, edges),
                current_histogram=_histogram_counts(current_values, edges),
            )
        )

    return comparisons
# docs:end compare_input_distribution


def _numeric_values(dataframe: pd.DataFrame, feature: str) -> list[float]:
    """Return non-null numeric values for one feature."""
    series = pd.to_numeric(dataframe[feature], errors="coerce").dropna()
    return [float(value) for value in series.to_list()]


def _mean(values: list[float]) -> float:
    """Return mean value, using 0.0 for an empty sequence."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _histogram_edges(values: list[float], bin_count: int) -> tuple[float, ...]:
    """Return equal-width histogram edges for the combined values."""
    if bin_count < 1:
        msg = "bin_count must be at least 1"
        raise ValueError(msg)
    if not values:
        return tuple(float(index) for index in range(bin_count + 1))

    minimum = min(values)
    maximum = max(values)
    if minimum == maximum:
        minimum -= 0.5
        maximum += 0.5
    width = (maximum - minimum) / bin_count
    return tuple(minimum + width * index for index in range(bin_count + 1))


def _histogram_counts(values: list[float], edges: tuple[float, ...]) -> tuple[int, ...]:
    """Count values per histogram bin."""
    counts = [0 for _ in range(len(edges) - 1)]
    for value in values:
        for index in range(len(edges) - 1):
            is_last_bin = index == len(edges) - 2
            if edges[index] <= value < edges[index + 1] or (
                is_last_bin and value == edges[index + 1]
            ):
                counts[index] += 1
                break
    return tuple(counts)


def _histogram_labels(edges: tuple[float, ...]) -> tuple[str, ...]:
    """Return readable histogram bin labels."""
    return tuple(
        f"{edges[index]:.2f}~{edges[index + 1]:.2f}"
        for index in range(len(edges) - 1)
    )
