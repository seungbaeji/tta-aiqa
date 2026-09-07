"""Keep the GE summary exercise starter red and the reference implementation green."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXERCISE_TESTS = ROOT / "labs/exercises/tests/test_ge_summary.py"
STARTER = ROOT / "labs/exercises"
SOLUTION = ROOT / "labs/solutions"


def _run_exercise(
    *pytest_args: str, interpret_root: Path
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(interpret_root)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(EXERCISE_TESTS), *pytest_args],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_starter_keeps_regression_green_and_current_goal_red() -> None:
    regression = _run_exercise("-m", "regression", interpret_root=STARTER)
    current_goal = _run_exercise("-m", "current_goal", interpret_root=STARTER)

    assert regression.returncode == 0, regression.stdout + regression.stderr
    assert current_goal.returncode != 0, current_goal.stdout + current_goal.stderr
    assert "AssertionError" in current_goal.stdout + current_goal.stderr


def test_reference_implementation_closes_the_current_goal() -> None:
    result = _run_exercise(interpret_root=SOLUTION)

    assert result.returncode == 0, result.stdout + result.stderr
