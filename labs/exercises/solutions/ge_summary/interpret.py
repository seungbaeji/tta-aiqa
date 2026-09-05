"""Read a reviewable Great Expectations summary without running the pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

REQUIRED_ROOT_KEYS: tuple[str, str, str, str] = (
    "success",
    "publish_blocking_gate",
    "raw_ingestion",
    "processed_readiness",
)


@dataclass(frozen=True)
class QualitySummaryInterpretation:
    """Parsed GE summary: checkpoint state plus whether it owns a publish decision."""

    raw_passed: bool
    processed_passed: bool
    overall_passed: bool
    is_publish_blocking_gate: bool
    supports_publish_decision: bool


def interpret_quality_summary(
    summary: Mapping[str, object],
) -> QualitySummaryInterpretation:
    """Interpret one reviewable GE summary mapping.

    Distinguishes checkpoint success from whether this artifact is a publish
    decision boundary. Does not run Great Expectations or write files.
    """

    if not isinstance(summary, Mapping):
        raise ValueError("quality summary must be a mapping")
    for key in REQUIRED_ROOT_KEYS:
        if key not in summary:
            raise ValueError(f"quality summary is missing required key: {key}")

    raw_passed = _scope_success(summary["raw_ingestion"], "raw_ingestion")
    processed_passed = _scope_success(
        summary["processed_readiness"], "processed_readiness"
    )
    overall_passed = raw_passed and processed_passed
    documented_success = _require_bool(summary["success"], "success")
    if documented_success is not overall_passed:
        raise ValueError("quality summary success does not match both scopes")
    is_publish_blocking_gate = _require_bool(
        summary["publish_blocking_gate"], "publish_blocking_gate"
    )
    return QualitySummaryInterpretation(
        raw_passed=raw_passed,
        processed_passed=processed_passed,
        overall_passed=overall_passed,
        is_publish_blocking_gate=is_publish_blocking_gate,
        supports_publish_decision=is_publish_blocking_gate,
    )


def _scope_success(scope: object, name: str) -> bool:
    if not isinstance(scope, Mapping):
        raise ValueError(f"{name} must be a mapping")
    if "success" not in scope:
        raise ValueError(f"{name} is missing required key: success")
    return _require_bool(scope["success"], f"{name}.success")


def _require_bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be an exact bool")
    return value
