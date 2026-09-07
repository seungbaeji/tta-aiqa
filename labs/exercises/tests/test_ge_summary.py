"""Exercise tests for reading a reviewable GE quality summary."""

from __future__ import annotations

from typing import Any

import pytest
from ge_summary import interpret_quality_summary


def _summary(
    *,
    success: bool = True,
    publish_blocking_gate: bool = False,
    raw_success: bool = True,
    processed_success: bool = True,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "success": success,
        "publish_blocking_gate": publish_blocking_gate,
        "raw_ingestion": {
            "success": raw_success,
            "statistics": {"evaluated_expectations": 8, "unsuccessful_expectations": 0},
            "profile": {"records": 4000, "maximum_minute": 2880},
        },
        "processed_readiness": {
            "success": processed_success,
            "statistics": {
                "evaluated_expectations": 57,
                "unsuccessful_expectations": 0,
            },
            "profile": {"rows": 4000, "feature_count": 133},
        },
    }


@pytest.mark.regression
def test_reads_canonical_scope_success_flags() -> None:
    reading = interpret_quality_summary(_summary())

    assert reading.raw_passed is True
    assert reading.processed_passed is True
    assert reading.overall_passed is True


@pytest.mark.regression
def test_mirrors_publish_blocking_gate_field() -> None:
    blocked = interpret_quality_summary(_summary(publish_blocking_gate=False))
    blocking = interpret_quality_summary(
        _summary(
            success=False,
            publish_blocking_gate=True,
            processed_success=False,
        )
    )

    assert blocked.is_publish_blocking_gate is False
    assert blocking.is_publish_blocking_gate is True


@pytest.mark.regression
def test_missing_required_key_raises_value_error() -> None:
    summary = _summary()
    del summary["raw_ingestion"]

    with pytest.raises(ValueError, match="raw_ingestion"):
        interpret_quality_summary(summary)


@pytest.mark.regression
def test_non_mapping_summary_raises_value_error() -> None:
    with pytest.raises(ValueError, match="mapping"):
        interpret_quality_summary(["not", "a", "mapping"])  # type: ignore[arg-type]


@pytest.mark.regression
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("success", 1),
        ("success", "true"),
        ("publish_blocking_gate", 0),
        ("publish_blocking_gate", "false"),
    ],
)
def test_non_bool_root_flags_are_rejected(field: str, value: object) -> None:
    summary = _summary()
    summary[field] = value

    with pytest.raises(ValueError, match="bool"):
        interpret_quality_summary(summary)


@pytest.mark.regression
def test_non_bool_scope_success_is_rejected() -> None:
    summary = _summary()
    summary["processed_readiness"]["success"] = 1

    with pytest.raises(ValueError, match="bool"):
        interpret_quality_summary(summary)


@pytest.mark.regression
def test_inconsistent_overall_success_raises_value_error() -> None:
    summary = _summary(success=False)

    with pytest.raises(ValueError, match="success"):
        interpret_quality_summary(summary)


@pytest.mark.regression
def test_does_not_mutate_input_summary() -> None:
    summary = _summary()
    original = {
        "success": summary["success"],
        "publish_blocking_gate": summary["publish_blocking_gate"],
        "raw_success": summary["raw_ingestion"]["success"],
        "processed_success": summary["processed_readiness"]["success"],
    }

    interpret_quality_summary(summary)

    assert summary["success"] is original["success"]
    assert summary["publish_blocking_gate"] is original["publish_blocking_gate"]
    assert summary["raw_ingestion"]["success"] is original["raw_success"]
    assert summary["processed_readiness"]["success"] is original["processed_success"]
    assert isinstance(summary, dict)


@pytest.mark.current_goal
def test_successful_scopes_do_not_support_publish_decision_when_gate_is_false() -> None:
    reading = interpret_quality_summary(
        _summary(success=True, publish_blocking_gate=False)
    )

    assert reading.overall_passed is True
    assert reading.is_publish_blocking_gate is False
    assert reading.supports_publish_decision is False


@pytest.mark.current_goal
def test_blocking_gate_supports_negative_publish_decision_when_checks_fail() -> None:
    reading = interpret_quality_summary(
        _summary(
            success=False,
            publish_blocking_gate=True,
            raw_success=True,
            processed_success=False,
        )
    )

    assert reading.overall_passed is False
    assert reading.is_publish_blocking_gate is True
    assert reading.supports_publish_decision is True


@pytest.mark.regression
def test_every_exercise_case_has_exactly_one_goal_marker(
    request: pytest.FixtureRequest,
) -> None:
    collected = [
        item
        for item in request.session.items
        if item.path == request.path
        and item.name != "test_every_exercise_case_has_exactly_one_goal_marker"
    ]
    for item in collected:
        markers = {marker.name for marker in item.iter_markers()}
        owned = markers & {"regression", "current_goal"}
        assert owned == {"regression"} or owned == {"current_goal"}, item.name
