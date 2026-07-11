"""Generate derived datasets used by the Simple MLOps demo."""

from __future__ import annotations

import argparse
from pathlib import Path

from aiqa_data import prepare_datasets


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Simple MLOps demo data.")
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help=(
            "Optional source CSV path. Defaults to "
            "data/human_vital_signs_dataset_2024.csv."
        ),
    )
    parser.add_argument(
        "--output-data-dir",
        type=Path,
        default=None,
        help=(
            "Optional output data directory. Defaults to the repository data "
            "directory."
        ),
    )
    args = parser.parse_args()

    for path in prepare_datasets(args.source, args.output_data_dir):
        print(path)


if __name__ == "__main__":
    main()
