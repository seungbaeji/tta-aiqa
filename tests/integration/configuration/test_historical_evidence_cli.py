"""Process-level safety checks for maintenance evidence scripts."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_builder_rejects_historical_output_before_reading_runtime_data() -> None:
    """A mistaken target path produces an actionable CLI error, not a traceback."""
    result = subprocess.run(
        (
            sys.executable,
            "scripts/build_data_evidence.py",
            "--output",
            "reference/evidence/data-lineage/accidental-rewrite.json",
        ),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "refusing to overwrite historical evidence" in result.stderr
    assert "Traceback" not in result.stderr
    accidental_output = (
        ROOT / "reference/evidence/data-lineage/accidental-rewrite.json"
    )
    assert not accidental_output.exists()
