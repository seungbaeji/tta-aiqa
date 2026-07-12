"""MLflow dataset source and digest compatibility adapters."""

from pathlib import Path
from typing import Any

from mlflow.data.dataset_source_registry import get_registered_sources


def local_dataset_source(path: Path) -> Any:
    """Create MLflow's registered local-artifact source for a CSV dataset path."""
    source_class = next(
        source
        for source in get_registered_sources()
        if source.__name__ == "LocalArtifactDatasetSource"
    )
    return source_class(path.resolve().as_uri())


def mlflow_dataset_digest(sha256: str | None) -> str | None:
    """Reduce a full SHA-256 value to MLflow's dataset digest length."""
    return sha256[:32] if sha256 else None
