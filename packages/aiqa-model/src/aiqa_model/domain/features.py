"""Versioned feature-selection policy values for model lifecycle configuration."""

from dataclasses import dataclass
from enum import StrEnum


class FeatureSelectionStrategy(StrEnum):
    """Supported feature-selection strategies for the course model lifecycle."""

    ALL_FROM_MODEL_INPUT_CONTRACT = "all_from_model_input_contract"


@dataclass(frozen=True)
class SelectedFeatureSet:
    """One named, frozen selection policy interpreted before model development."""

    name: str
    strategy: FeatureSelectionStrategy
    rationale: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.name, str)
            or not self.name
            or self.name != self.name.strip()
        ):
            raise ValueError("feature-set name must be a non-empty trimmed string")
        if not isinstance(self.strategy, FeatureSelectionStrategy):
            raise ValueError("feature-set strategy must be a FeatureSelectionStrategy")
        if (
            not isinstance(self.rationale, str)
            or not self.rationale
            or self.rationale != self.rationale.strip()
        ):
            raise ValueError("feature-set rationale must be a non-empty trimmed string")


@dataclass(frozen=True)
class FeatureSetCatalog:
    """Named feature-selection policies with one canonical model input choice."""

    canonical_feature_set: str
    feature_sets: tuple[SelectedFeatureSet, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.canonical_feature_set, str)
            or not self.canonical_feature_set
            or self.canonical_feature_set != self.canonical_feature_set.strip()
        ):
            raise ValueError("canonical feature set must be a non-empty trimmed string")
        if not isinstance(self.feature_sets, tuple) or not self.feature_sets:
            raise ValueError("feature-set catalog requires at least one feature set")
        if any(not isinstance(item, SelectedFeatureSet) for item in self.feature_sets):
            raise ValueError("feature-set catalog contains an invalid feature set")
        names = tuple(item.name for item in self.feature_sets)
        if len(names) != len(set(names)):
            raise ValueError("feature-set names must be unique")
        if self.canonical_feature_set not in names:
            raise ValueError("canonical feature set must name a declared feature set")

    @property
    def canonical(self) -> SelectedFeatureSet:
        """Return the one selected feature policy in deterministic config order."""
        return next(
            item
            for item in self.feature_sets
            if item.name == self.canonical_feature_set
        )
