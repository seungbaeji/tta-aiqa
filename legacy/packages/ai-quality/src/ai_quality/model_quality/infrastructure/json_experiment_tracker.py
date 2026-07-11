"""JSON experiment tracker used when MLflow is not required."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ai_quality.common.artifacts import ensure_artifact_dir
from ai_quality.model_quality.ports.experiment_tracker import (
    DatasetInput,
    ModelArtifact,
    ScalarValue,
)


@dataclass(frozen=True)
class JsonExperimentTracker:
    """Persist experiment context as a JSON artifact."""

    output_dir: Path

    @classmethod
    def for_chapter(cls, chapter_name: str) -> JsonExperimentTracker:
        """Create a tracker under artifacts."""
        return cls(output_dir=ensure_artifact_dir("experiments", chapter_name))

    def log_run(
        self,
        run_name: str,
        params: Mapping[str, ScalarValue],
        metrics: Mapping[str, float],
        artifacts: Sequence[Path] = (),
        datasets: Sequence[DatasetInput] = (),
        model_artifact: ModelArtifact | None = None,
        tags: Mapping[str, ScalarValue] | None = None,
    ) -> Path:
        """Write one experiment run as JSON."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / f"{run_name}.json"
        payload = {
            "run_name": run_name,
            "params": dict(params),
            "metrics": dict(metrics),
            "artifacts": [str(path) for path in artifacts],
            "datasets": [
                {
                    "name": dataset.name,
                    "version": dataset.version,
                    "path": str(dataset.path),
                    "context": dataset.context,
                    "target_column": dataset.target_column,
                    "digest": dataset.digest,
                }
                for dataset in datasets
            ],
            "model_artifact": (
                {
                    "name": model_artifact.name,
                    "version": model_artifact.version,
                    "path": str(model_artifact.path),
                }
                if model_artifact is not None
                else None
            ),
            "tags": dict(tags or {}),
        }
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return output_path
