"""Command-line entry point for the PhysioNet 2012 Phase 0 experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.phase0.config import load_config
from scripts.phase0.data import prepare_data
from scripts.phase0.modeling import evaluate_models
from scripts.phase0.reporting import write_data_artifacts, write_model_evidence

DEFAULT_CONFIG = Path("configs/phase0/physionet-2012.yaml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--stage",
        choices=("data", "all"),
        default="all",
        help="Run only F0 data preparation or the complete F0-F2 experiment.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    prepared = prepare_data(config)
    outputs = write_data_artifacts(prepared, config)
    result = {
        "f0_passed": prepared.profile["f0_passed"],
        "outputs": outputs,
    }
    if args.stage == "all":
        evaluation = evaluate_models(prepared.features, prepared.splits, config)
        result["outputs"].update(write_model_evidence(prepared, evaluation, config))
        result["f1_passed"] = evaluation.report["gates"]["f1_predictive_feasibility"][
            "passed"
        ]
        result["f2_passed"] = evaluation.report["gates"]["f2_scenario_feasibility"][
            "passed"
        ]
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
