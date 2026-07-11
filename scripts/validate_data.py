"""Run V2 raw and processed GE checkpoints with repository defaults."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "data_quality_pipeline.main",
            "validate",
            "--source-contract",
            str(ROOT / "configs/contracts/physionet-record.yaml"),
            "--aggregation-config",
            str(ROOT / "configs/data/aggregation.yaml"),
            "--split-config",
            str(ROOT / "params.yaml"),
            "--patient-features",
            str(ROOT / "data/processed/physionet-2012/patient-features.csv"),
            "--split-manifest",
            str(ROOT / "data/splits/physionet-2012/split-manifest.csv"),
            "--split-dataset-dir",
            str(ROOT / "data/splits/physionet-2012/datasets"),
            "--source-evidence",
            str(ROOT / "artifacts/data-quality/source-integrity.json"),
            "--quality-rules",
            str(ROOT / "configs/data/quality-rules.yaml"),
            "--validation-artifact-dir",
            str(ROOT / "artifacts/data-quality/great-expectations"),
        ],
        check=True,
        cwd=ROOT,
    )


if __name__ == "__main__":
    main()
