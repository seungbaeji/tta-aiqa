"""Build reviewable GE evidence without committing runtime Data Docs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import great_expectations

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    runtime_path = (
        ROOT / "artifacts/data-quality/great-expectations/validation-summary.json"
    )
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    document = {
        "schema_version": 1,
        "great_expectations_version": great_expectations.__version__,
        "success": runtime["success"],
        "publish_blocking_gate": runtime["publish_blocking_gate"],
        "configuration": {
            "quality_rules_sha256": sha256(ROOT / "configs/data/quality-rules.yaml"),
            "aggregation_sha256": sha256(ROOT / "configs/data/aggregation.yaml"),
        },
        "raw_ingestion": {
            "success": runtime["raw_ingestion"]["success"],
            "statistics": runtime["raw_ingestion"]["statistics"],
            "profile": runtime["profile"]["raw"],
        },
        "processed_readiness": {
            "success": runtime["processed_readiness"]["success"],
            "statistics": runtime["processed_readiness"]["statistics"],
            "profile": runtime["profile"]["processed"],
        },
    }
    output = ROOT / "reference/evidence/data-quality/ge-validation-summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
