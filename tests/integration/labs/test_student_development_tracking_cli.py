"""CLI contract for the student development tracking module."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "labs/run/log_development.py"


@pytest.mark.integration
def test_cli_reports_not_running_without_tracking_uri() -> None:
    features = ROOT / "data/features.csv"
    if not features.is_file():
        pytest.skip("course data is not materialized")
    env = os.environ.copy()
    env.pop("AIQA_MLFLOW_TRACKING_URI", None)
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result["status"] == "MLFLOW_NOT_RUNNING"
    assert result["student_run_id"] is None
    assert result["official_train_run"]
    assert result["official_final_run"]
    assert result["student_run_id"] != result["official_train_run"]
    assert result["accessed_roles"] == "train,valid"
    assert result["experiment_name"] == "student-development-tracking"
    assert "sqlite:///" not in completed.stdout
