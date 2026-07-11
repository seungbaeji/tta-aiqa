"""Dashboard importer command-line behavior tests."""

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
