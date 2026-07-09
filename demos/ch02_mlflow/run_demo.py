"""Chapter 2 Demo: inspect MLflow-compatible evaluation records."""

from __future__ import annotations

from ai_quality.labs.ch02_model_quality import (
    print_report,
    record_model_test_evaluation,
)


def main() -> None:
    """Run the same recording step used by the chapter 2 model-quality Lab."""
    result = record_model_test_evaluation()

    print_report(result.report)
    print("dataset lineage")
    print(f"version={result.dataset_version}")
    print(f"digest={result.dataset_digest}")
    print(f"model_version={result.model_version}")
    print("experiment artifact")
    print(result.json_path)
    if result.mlflow_path is not None:
        tracking_uri = (
            result.mlflow_tracking_uri
            or "sqlite:///" + str(result.mlflow_path)
        )
        print("mlflow tracking")
        print(tracking_uri)
        print("mlflow run contents")
        print("params, metrics, dataset input, tags, JSON artifact, sklearn model")
    else:
        if result.mlflow_tracking_uri is None:
            print("mlflow package is not installed. JSON artifact was created.")
        else:
            print(
                "mlflow tracking was configured but skipped due to connection or "
                "server error. JSON artifact was created."
            )


if __name__ == "__main__":
    main()
