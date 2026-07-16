"""Course setup state contract tests."""

from scripts.setup_course import missing_notebook_runtime_modules, verify_course_state


def test_course_state_has_v2_decisions_without_generated_model() -> None:
    state = verify_course_state(require_model=False)

    assert state["canonical_decisions"] == {
        "candidate-a": "HOLD",
        "candidate-b": "APPROVE",
    }
    assert state["deployed_model"] == "not_required"
    assert state["notebook_runtime"] == "ready"


def test_notebook_runtime_reports_only_missing_modules() -> None:
    """Course setup names the exact dependency group gap before data preparation."""
    available = {"ipykernel", "nbformat"}

    assert missing_notebook_runtime_modules(
        lambda module: object() if module in available else None
    ) == ("nbclient",)
