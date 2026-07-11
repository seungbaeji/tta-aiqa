"""Train a risk model and publish the latest model artifact."""

from __future__ import annotations

import argparse
import json
import os
import time

from aiqa_model import TrainConfig, train_once, wait_for_mlflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train and log a risk model.")
    parser.add_argument("--train-path", default="/app/data/vital_signs_train.csv")
    parser.add_argument("--test-path", default="/app/data/vital_signs_test.csv")
    parser.add_argument(
        "--model-path",
        default=os.getenv("MODEL_PATH", "/app/models/latest_model.joblib"),
    )
    parser.add_argument(
        "--metadata-path",
        default=os.getenv("METADATA_PATH", "/app/models/latest_metadata.json"),
    )
    parser.add_argument(
        "--tracking-uri",
        default=os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"),
    )
    parser.add_argument("--experiment", default="simple-aiqa-risk-classifier")
    parser.add_argument("--repeat", type=int, default=1, help="0 means forever")
    parser.add_argument("--interval", type=float, default=60.0)
    parser.add_argument(
        "--train-sample-size",
        type=int,
        default=int(os.getenv("TRAIN_SAMPLE_SIZE", "50000")),
    )
    parser.add_argument(
        "--test-sample-size",
        type=int,
        default=int(os.getenv("TEST_SAMPLE_SIZE", "10000")),
    )
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=int(os.getenv("N_ESTIMATORS", "40")),
    )
    return parser.parse_args()


def train_config(args: argparse.Namespace) -> TrainConfig:
    return TrainConfig(
        train_path=args.train_path,
        test_path=args.test_path,
        model_path=args.model_path,
        metadata_path=args.metadata_path,
        tracking_uri=args.tracking_uri,
        experiment=args.experiment,
        train_sample_size=args.train_sample_size,
        test_sample_size=args.test_sample_size,
        n_estimators=args.n_estimators,
    )


def main() -> None:
    args = parse_args()
    config = train_config(args)
    wait_for_mlflow(config.tracking_uri)

    run_index = 0
    while args.repeat == 0 or run_index < args.repeat:
        run_index += 1
        metadata = train_once(config, run_index)
        print(
            json.dumps(
                {
                    "model_path": config.model_path,
                    "metadata_path": config.metadata_path,
                    "run_id": metadata["run_id"],
                    "metrics": metadata["metrics"],
                },
                ensure_ascii=False,
            )
        )
        if args.repeat == 0 or run_index < args.repeat:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
