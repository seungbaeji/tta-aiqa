"""Train the tree-based baseline model used by model and serving labs."""

from __future__ import annotations

from ai_quality.labs.ch02_model_quality import (
    chapter_model_path,
    feature_columns,
    load_dataset,
    target_column,
)
from ai_quality.model_quality.infrastructure.sklearn_classifier import (
    save_model,
    train_sklearn_classifier,
)


def main() -> None:
    """Train and save the RandomForest baseline classifier."""
    dataframe = load_dataset("vital_signs_train.csv")
    features = feature_columns()
    target = target_column()

    model = train_sklearn_classifier(
        dataframe=dataframe,
        feature_columns=features,
        target_column=target,
    )
    output_path = save_model(model, chapter_model_path())

    print(f"trained_rows={len(dataframe)}")
    print(f"features={features}")
    print(f"model_path={output_path}")


if __name__ == "__main__":
    main()
