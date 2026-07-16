"""Prepare reproducible course data and verify the baseline classroom state."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COURSE_SETUP_SCRIPTS = ("prepare_data.py", "validate_data.py")
NOTEBOOK_RUNTIME_MODULES = ("ipykernel", "nbclient", "nbformat")


def run_script(name: str) -> None:
    """Run one course preparation script from the repository root."""
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / name)],
        cwd=ROOT,
        check=True,
    )


def missing_notebook_runtime_modules(
    finder: Callable[[str], object | None] = find_spec,
) -> tuple[str, ...]:
    """Return notebook modules that must be installed before guided labs begin."""
    return tuple(
        module for module in NOTEBOOK_RUNTIME_MODULES if finder(module) is None
    )


def assert_notebook_runtime() -> None:
    """Stop setup early when the documented notebook environment is incomplete."""
    missing = missing_notebook_runtime_modules()
    if missing:
        modules = ", ".join(missing)
        raise RuntimeError(
            f"notebook runtime is missing: {modules}. "
            "Run `uv sync --all-packages --group notebook` and retry."
        )


def verify_course_state(*, require_model: bool) -> dict[str, object]:
    """Verify the prepared data, evidence, and optionally provisioned baseline model."""
    canonical_path = (
        ROOT / "docs/reference/evidence/model/revisions/v2/canonical-benchmark.json"
    )
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    decisions = {
        item["profile"]: item["decision"] for item in canonical["decisions"]
    }
    if decisions != {"candidate-a": "HOLD", "candidate-b": "APPROVE"}:
        raise RuntimeError("canonical V2 release decisions do not match the course")

    deployed_metadata = (
        ROOT / "artifacts/models/revisions/v2/deployed/metadata.json"
    )
    model_status = "not_required"
    if require_model:
        if not deployed_metadata.is_file():
            raise FileNotFoundError(
                "baseline model is not provisioned; use --data-only "
                "outside the course VM"
            )
        metadata = json.loads(deployed_metadata.read_text(encoding="utf-8"))
        if metadata.get("profile") != "baseline":
            raise RuntimeError("course VM must start with the baseline model")
        model_status = "baseline_ready"

    return {
        "schema_version": 1,
        "data_pipeline": "ready",
        "great_expectations": "ready",
        "notebook_runtime": "ready",
        "canonical_decisions": decisions,
        "deployed_model": model_status,
    }


def main() -> None:
    """Prepare student-local data without rewriting historical course evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-only",
        action="store_true",
        help="prepare data and GE without requiring the provisioned baseline model",
    )
    args = parser.parse_args()
    assert_notebook_runtime()
    for script in COURSE_SETUP_SCRIPTS:
        run_script(script)
    print(
        json.dumps(
            verify_course_state(require_model=not args.data_only),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
