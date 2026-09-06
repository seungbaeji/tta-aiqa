"""Generate the canonical model input contract from the v1 available features."""

from __future__ import annotations

from pathlib import Path

import yaml
from aiqa_data.adapters import load_aggregation_plan

ROOT = Path(__file__).resolve().parents[1]
CATEGORICAL = {"gender", "icu_type"}


def main() -> None:
    plan = load_aggregation_plan(ROOT / "configs/data/aggregation.yaml")
    document = {
        "schema_version": 1,
        "name": "physionet-2012-canonical-v1",
        "target": "target",
        "features": [
            {
                "name": name,
                "dtype": (
                    "boolean"
                    if name.endswith("__missing")
                    else "category"
                    if name in CATEGORICAL
                    else "float"
                ),
                "nullable": not name.endswith("__missing"),
            }
            for name in plan.feature_names
        ],
    }
    output = ROOT / "configs/contracts/model-input.yaml"
    output.write_text(
        yaml.safe_dump(document, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
