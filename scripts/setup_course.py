"""Prepare reproducible course data and verify the baseline classroom state."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_script(name: str) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / name)],
        cwd=ROOT,
        check=True,
    )


def verify_course_state(*, require_model: bool) -> dict[str, object]:
    canonical_path = (
        ROOT / "reference/evidence/model/revisions/v2/canonical-benchmark.json"
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
        "canonical_decisions": decisions,
        "deployed_model": model_status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-only",
        action="store_true",
        help="prepare data and GE without requiring the provisioned baseline model",
    )
    args = parser.parse_args()
    run_script("prepare_data.py")
    run_script("build_data_evidence.py")
    run_script("build_split_revision_evidence.py")
    run_script("validate_data.py")
    run_script("build_quality_evidence.py")
    print(
        json.dumps(
            verify_course_state(require_model=not args.data_only),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
