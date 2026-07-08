"""Experiment tracking port."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

ScalarValue = str | int | float | bool


class ExperimentTracker(Protocol):
    """Record experiment context and metrics."""

    def log_run(
        self,
        run_name: str,
        params: Mapping[str, ScalarValue],
        metrics: Mapping[str, float],
        artifacts: Sequence[Path] = (),
    ) -> Path | None:
        """Record one experiment run."""
        ...
