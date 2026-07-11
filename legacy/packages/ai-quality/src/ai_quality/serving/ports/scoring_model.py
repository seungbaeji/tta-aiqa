"""Scoring model port."""

from __future__ import annotations

from typing import Protocol


class ScoringModel(Protocol):
    """Return positive-class scores from feature dictionaries."""

    def score_one(self, features: dict[str, float]) -> float:
        """Return one positive-class score."""
        ...
