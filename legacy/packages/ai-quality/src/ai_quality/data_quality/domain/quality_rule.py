"""Data quality rule definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NumericRange:
    """Allowed range for a numeric feature."""

    column: str
    min_value: float
    max_value: float

    def contains(self, value: float) -> bool:
        """Return whether a numeric value is inside the allowed range."""
        return self.min_value <= value <= self.max_value


@dataclass(frozen=True)
class DataQualityRules:
    """Rule set used before model evaluation."""

    valid_ranges: tuple[NumericRange, ...]
    allowed_labels: tuple[str, ...]
    minimum_positive_support: int
    maximum_missing_ratio: float

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> DataQualityRules:
        """Build data quality rules from the course config."""
        valid_ranges = tuple(
            NumericRange(
                column=str(column),
                min_value=float(values["min"]),
                max_value=float(values["max"]),
            )
            for column, values in config.get("valid_ranges", {}).items()
        )

        return cls(
            valid_ranges=valid_ranges,
            allowed_labels=tuple(config["allowed_labels"]),
            minimum_positive_support=int(config["minimum_positive_support"]),
            maximum_missing_ratio=float(config["maximum_missing_ratio"]),
        )

    def range_for(self, column: str) -> NumericRange | None:
        """Return a numeric range rule for a column if one exists."""
        for valid_range in self.valid_ranges:
            if valid_range.column == column:
                return valid_range
        return None
