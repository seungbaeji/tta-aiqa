"""Experiment tracking port."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

ScalarValue = str | int | float | bool


@dataclass(frozen=True)
class DatasetInput:
    """Dataset lineage metadata to attach to an experiment run."""

    name: str
    version: str
    path: Path
    context: str
    target_column: str | None = None
    digest: str | None = None
    dataframe: Any | None = None


@dataclass(frozen=True)
class ModelArtifact:
    """Model metadata and examples to attach to an experiment run."""

    name: str
    version: str
    path: Path
    model: Any | None = None
    input_example: Any | None = None
    output_example: Any | None = None


class ExperimentTracker(Protocol):
    """Record experiment context and metrics."""

    def log_run(
        self,
        run_name: str,
        params: Mapping[str, ScalarValue],
        metrics: Mapping[str, float],
        artifacts: Sequence[Path] = (),
        datasets: Sequence[DatasetInput] = (),
        model_artifact: ModelArtifact | None = None,
        tags: Mapping[str, ScalarValue] | None = None,
    ) -> Path | None:
        """Record one experiment run."""
        ...
