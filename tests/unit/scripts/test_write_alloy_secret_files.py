"""Write Grafana Cloud values into Alloy secret files without exposing them."""

from __future__ import annotations

import re
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/platform/write_alloy_secret_files.sh"

ASSIGNMENTS = {
    "METRICS_URL": " https://prometheus.example/api/prom/push ",
    "METRICS_USERNAME": "111",
    "LOGS_URL": "https://logs.example/loki/api/v1/push",
    "LOGS_USERNAME": "222",
    "OTLP_URL": "https://otlp.example/otlp",
    "OTLP_USERNAME": "333",
    "API_KEY": "glc_example",
}


def filled_script(tmp_path: Path) -> Path:
    source = SCRIPT.read_text(encoding="utf-8")
    for name, value in ASSIGNMENTS.items():
        source = re.sub(
            rf'^{name}=""$',
            f'{name}="{value}"',
            source,
            count=1,
            flags=re.MULTILINE,
        )
    path = tmp_path / "write_alloy_secret_files.sh"
    path.write_text(source, encoding="utf-8")
    return path


def test_write_secret_files_trims_values_and_sets_owner_mode(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "secrets"
    result = subprocess.run(
        ["bash", str(filled_script(tmp_path)), str(output_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "glc_example" not in result.stdout
    assert (output_dir / "metrics-url").read_text(encoding="utf-8") == (
        "https://prometheus.example/api/prom/push\n"
    )
    assert (output_dir / "api-key").read_text(encoding="utf-8") == "glc_example\n"
    mode = stat.S_IMODE((output_dir / "api-key").stat().st_mode)
    assert mode == 0o600


def test_empty_script_variables_fail_before_writing(tmp_path: Path) -> None:
    output_dir = tmp_path / "secrets"
    result = subprocess.run(
        ["bash", str(SCRIPT), str(output_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "API_KEY" in result.stderr
    assert not output_dir.exists()
