"""Cross-platform wrapper for the versioned data pipeline."""

from __future__ import annotations

import subprocess
from pathlib import Path

from aiqa_data.adapters import acquire_source_manifest, verify_source_manifest

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "data/raw/physionet-2012/source-manifest.yaml"


def main() -> None:
    acquire_source_manifest(SOURCE_MANIFEST)
    verify_source_manifest(SOURCE_MANIFEST)
    subprocess.run(["dvc", "repro"], check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
