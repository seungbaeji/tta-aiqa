"""Opaque fitted-model values transferred between lifecycle capabilities."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class FittedModels:
    """Deterministic named collection of opaque fitted model artifacts."""

    items: tuple[tuple[str, object], ...]

    def __post_init__(self) -> None:
        names = tuple(name for name, _ in self.items)
        if not names or any(
            not isinstance(name, str) or not name or name != name.strip()
            for name in names
        ):
            raise ValueError("fitted models require at least one named model")
        if len(names) != len(set(names)):
            raise ValueError("fitted model names must be unique")
        if names != tuple(sorted(names)):
            raise ValueError("fitted model names must be sorted")

    @classmethod
    def from_mapping(cls, models: Mapping[str, object]) -> FittedModels:
        """Create a deterministic named collection from profile-to-model artifacts."""
        return cls(tuple(sorted(models.items())))

    @property
    def names(self) -> tuple[str, ...]:
        """Return fitted profile names in deterministic order."""
        return tuple(name for name, _ in self.items)

    def get(self, name: str) -> object:
        """Return the opaque fitted artifact for a configured profile."""
        for profile, model in self.items:
            if profile == name:
                return model
        raise KeyError(f"fitted model profile does not exist: {name}")
