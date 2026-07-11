"""Validation result objects for expectation-style reports."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpectationCheckResult:
    """One validation rule result shown in the chapter 2 demo."""

    expectation_type: str
    column: str
    success: bool
    unexpected_count: int
    unexpected_ratio: float
    observed_value: str
    qa_reason: str


@dataclass(frozen=True)
class ValidationResult:
    """Dataset-level validation result."""

    dataset_name: str
    row_count: int
    expectation_results: tuple[ExpectationCheckResult, ...]

    @property
    def success(self) -> bool:
        """Return whether all expectations passed."""
        return all(result.success for result in self.expectation_results)

    @property
    def success_count(self) -> int:
        """Return successful expectation count."""
        return sum(1 for result in self.expectation_results if result.success)

    @property
    def failure_count(self) -> int:
        """Return failed expectation count."""
        return sum(1 for result in self.expectation_results if not result.success)
