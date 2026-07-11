"""Build expectation-style validation results from quality reports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ai_quality.data_quality.domain.quality_report import (
    ColumnQuality,
    QualityReport,
    RangeCheckResult,
)
from ai_quality.data_quality.domain.validation_result import (
    ExpectationCheckResult,
    ValidationResult,
)


def build_validation_result(
    report: QualityReport,
    expectations: Sequence[Mapping[str, Any]],
    dataset_name: str,
) -> ValidationResult:
    """Build validation results for configured expectations."""
    results = tuple(
        build_expectation_check_result(report, expectation)
        for expectation in expectations
    )
    return ValidationResult(
        dataset_name=dataset_name,
        row_count=report.row_count,
        expectation_results=results,
    )


def build_expectation_check_result(
    report: QualityReport,
    expectation: Mapping[str, Any],
) -> ExpectationCheckResult:
    """Build one expectation check result."""
    expectation_type = str(expectation["expectation_type"])
    column = str(expectation["column"])
    qa_reason = str(expectation.get("qa_reason", ""))

    if expectation_type == "expect_column_to_exist":
        return build_column_exists_result(report, expectation_type, column, qa_reason)
    if expectation_type == "expect_column_values_to_not_be_null":
        return build_not_null_result(report, expectation_type, column, qa_reason)
    if expectation_type == "expect_column_values_to_be_in_set":
        return build_allowed_label_result(report, expectation_type, column, qa_reason)
    if expectation_type == "expect_column_values_to_be_between":
        return build_range_result(report, expectation_type, column, qa_reason)

    msg = f"Unsupported expectation type: {expectation_type}"
    raise ValueError(msg)


def build_column_exists_result(
    report: QualityReport,
    expectation_type: str,
    column: str,
    qa_reason: str,
) -> ExpectationCheckResult:
    """Build a column existence result."""
    missing = column in report.missing_columns
    return ExpectationCheckResult(
        expectation_type=expectation_type,
        column=column,
        success=not missing,
        unexpected_count=1 if missing else 0,
        unexpected_ratio=100.0 if missing else 0.0,
        observed_value="missing" if missing else "exists",
        qa_reason=qa_reason,
    )


def build_not_null_result(
    report: QualityReport,
    expectation_type: str,
    column: str,
    qa_reason: str,
) -> ExpectationCheckResult:
    """Build a not-null validation result."""
    column_quality = find_column_quality(report, column)
    missing_count = (
        report.row_count
        if column_quality is None
        else column_quality.missing_count
    )
    missing_ratio = (
        missing_count / report.row_count * 100
        if report.row_count > 0
        else 0.0
    )

    return ExpectationCheckResult(
        expectation_type=expectation_type,
        column=column,
        success=missing_count == 0,
        unexpected_count=missing_count,
        unexpected_ratio=missing_ratio,
        observed_value=f"missing_count={missing_count}",
        qa_reason=qa_reason,
    )


def build_allowed_label_result(
    report: QualityReport,
    expectation_type: str,
    column: str,
    qa_reason: str,
) -> ExpectationCheckResult:
    """Build a label-set validation result."""
    invalid_count = report.label_support.invalid_count
    invalid_ratio = (
        invalid_count / report.row_count * 100
        if report.row_count > 0
        else 0.0
    )
    return ExpectationCheckResult(
        expectation_type=expectation_type,
        column=column,
        success=invalid_count == 0,
        unexpected_count=invalid_count,
        unexpected_ratio=invalid_ratio,
        observed_value=f"invalid_count={invalid_count}",
        qa_reason=qa_reason,
    )


def build_range_result(
    report: QualityReport,
    expectation_type: str,
    column: str,
    qa_reason: str,
) -> ExpectationCheckResult:
    """Build a numeric range validation result."""
    range_result = find_range_result(report, column)
    invalid_count = (
        report.row_count
        if range_result is None
        else range_result.invalid_count
    )
    invalid_ratio = (
        invalid_count / report.row_count * 100
        if report.row_count > 0
        else 0.0
    )
    observed_value = (
        "missing range result"
        if range_result is None
        else f"allowed={range_result.min_value:g}..{range_result.max_value:g}"
    )
    return ExpectationCheckResult(
        expectation_type=expectation_type,
        column=column,
        success=invalid_count == 0,
        unexpected_count=invalid_count,
        unexpected_ratio=invalid_ratio,
        observed_value=observed_value,
        qa_reason=qa_reason,
    )


def find_column_quality(
    report: QualityReport,
    column: str,
) -> ColumnQuality | None:
    """Return column quality for one column."""
    for column_quality in report.column_quality:
        if column_quality.column == column:
            return column_quality
    return None


def find_range_result(
    report: QualityReport,
    column: str,
) -> RangeCheckResult | None:
    """Return range result for one column."""
    for range_result in report.range_results:
        if range_result.column == column:
            return range_result
    return None
