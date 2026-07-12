"""Dashboard importer command-line behavior tests."""

import os
import subprocess


def test_dashboard_cli_help_does_not_require_grafana_credentials() -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "--package",
            "aiqa-grafana-dashboard-importer",
            "aiqa-grafana-dashboard",
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--check" in result.stdout
    assert "validation error" not in result.stderr.lower()


def test_dashboard_cli_check_explains_missing_student_configuration() -> None:
    """A first-time student gets a setup action instead of a Pydantic traceback."""
    result = subprocess.run(
        [
            "uv",
            "run",
            "--package",
            "aiqa-grafana-dashboard-importer",
            "aiqa-grafana-dashboard",
            "--check",
        ],
        check=False,
        capture_output=True,
        text=True,
        env={
            key: value
            for key, value in os.environ.items()
            if not key.startswith("AIQA_GRAFANA_")
        },
    )

    assert result.returncode == 2
    assert ".env.grafanacloud.example" in result.stderr
    assert "Traceback" not in result.stderr
