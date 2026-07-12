"""Course setup state contract tests."""

from scripts.setup_course import verify_course_state


def test_course_state_has_v2_decisions_without_generated_model() -> None:
    state = verify_course_state(require_model=False)

    assert state["canonical_decisions"] == {
        "candidate-a": "HOLD",
        "candidate-b": "APPROVE",
    }
    assert state["deployed_model"] == "not_required"
