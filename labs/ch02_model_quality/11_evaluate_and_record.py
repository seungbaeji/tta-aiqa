"""Evaluate the chapter 2 scikit-learn baseline and record the run context."""

from __future__ import annotations

from ai_quality.labs.ch02_model_quality import (
    print_report,
    record_model_test_evaluation,
)


def main() -> None:
    """Evaluate the baseline model and write JSON or MLflow tracking records."""
    result = record_model_test_evaluation()

    print_report(result.report)
    print("dataset lineage")
    print(f"version={result.dataset_version}")
    print(f"digest={result.dataset_digest}")
    print(f"model_version={result.model_version}")
    print("experiment artifact")
    print(result.json_path)
    if result.mlflow_path is not None:
        print("mlflow tracking")
        print(result.mlflow_path)
    else:
        print("mlflow package is not installed. JSON artifact was created.")


if __name__ == "__main__":
    main()
