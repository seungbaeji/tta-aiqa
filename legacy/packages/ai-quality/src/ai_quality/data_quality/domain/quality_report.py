"""Data quality report value objects."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ai_quality.common.labels import NEGATIVE_LABEL, POSITIVE_LABEL, normalize_label


@dataclass(frozen=True)
class ColumnQuality:
    """Quality summary for a single column."""

    column: str
    dtype: str
    missing_count: int
    missing_ratio: float
    unique_count: int


@dataclass(frozen=True)
class RangeCheckResult:
    """Range validation result for a numeric column."""

    column: str
    min_value: float
    max_value: float
    invalid_count: int
    invalid_ratio: float


@dataclass(frozen=True)
class LabelSupport:
    """Label distribution summary."""

    positive_label: str
    negative_label: str
    positive_count: int
    negative_count: int
    invalid_count: int
    missing_count: int

    @property
    def labeled_count(self) -> int:
        """Return the number of rows with allowed labels."""
        return self.positive_count + self.negative_count

    @property
    def positive_rate(self) -> float:
        """Return positive support ratio in percent."""
        if self.labeled_count == 0:
            return 0.0
        return self.positive_count / self.labeled_count * 100.0


@dataclass(frozen=True)
class QualityReport:
    """Complete data quality report used before model evaluation."""

    row_count: int
    column_count: int
    missing_columns: tuple[str, ...]
    column_quality: tuple[ColumnQuality, ...]
    range_results: tuple[RangeCheckResult, ...]
    label_support: LabelSupport

    @property
    def is_evaluation_ready(self) -> bool:
        """Return whether the dataset is ready for basic model evaluation."""
        return (
            not self.missing_columns
            and self.label_support.invalid_count == 0
            and self.label_support.missing_count == 0
            and self.label_support.positive_count > 0
        )


# docs:start calculate_label_support
def calculate_label_support(
    labels: Sequence[object],
    positive_label: str = POSITIVE_LABEL,
    negative_label: str = NEGATIVE_LABEL,
) -> LabelSupport:
    """Count positive, negative, invalid, and missing labels."""
    positive_count = 0
    negative_count = 0
    invalid_count = 0
    missing_count = 0

    for value in labels:
        normalized = normalize_label(value)
        if normalized is None:
            missing_count += 1
        elif normalized == positive_label:
            positive_count += 1
        elif normalized == negative_label:
            negative_count += 1
        else:
            invalid_count += 1

    return LabelSupport(
        positive_label=positive_label,
        negative_label=negative_label,
        positive_count=positive_count,
        negative_count=negative_count,
        invalid_count=invalid_count,
        missing_count=missing_count,
    )
# docs:end calculate_label_support

