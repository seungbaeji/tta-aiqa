"""Model lifecycle requests and sealed-test acknowledgement values."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

SEALED_TEST_CONFIRMATION_TOKEN = "CONFIRM-FROZEN-CANONICAL-TEST"


class ModelDatasetRole(StrEnum):
    """Dataset roles as they are consumed by the model lifecycle."""

    TRAIN = "train"
    VALID = "valid"
    TEST = "test"


DEVELOPMENT_DATASET_ROLES = (
    ModelDatasetRole.TRAIN.value,
    ModelDatasetRole.VALID.value,
)
FINALIZATION_DATASET_ROLES = (*DEVELOPMENT_DATASET_ROLES, ModelDatasetRole.TEST.value)


@dataclass(frozen=True)
class ModelProfileSelection:
    """A deterministic non-empty set of configured model profile names."""

    names: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.names, tuple) or not self.names:
            raise ValueError("model profile selection requires at least one name")
        if any(
            not isinstance(name, str) or not name or name != name.strip()
            for name in self.names
        ):
            raise ValueError("model profile names must be non-empty trimmed strings")
        if len(self.names) != len(set(self.names)):
            raise ValueError("model profile selection names must be unique")
        if self.names != tuple(sorted(self.names)):
            raise ValueError("model profile selection names must be sorted")

    @classmethod
    def from_names(cls, names: Iterable[str]) -> ModelProfileSelection:
        """Create a deterministic selection from configured profile names."""
        return cls(tuple(sorted(names)))


@dataclass(frozen=True)
class FeatureDiagnosticsRequest:
    """Name the baseline and candidate profiles compared during development only."""

    baseline_profile: str
    candidate_profile: str

    def __post_init__(self) -> None:
        values = (self.baseline_profile, self.candidate_profile)
        if any(
            not isinstance(value, str) or not value or value != value.strip()
            for value in values
        ):
            raise ValueError(
                "diagnostic profile names must be non-empty trimmed strings"
            )
        if self.baseline_profile == self.candidate_profile:
            raise ValueError("feature diagnostics require distinct profile names")


@dataclass(frozen=True)
class SealedTestConfirmation:
    """Explicit acknowledgement required before the canonical test is opened."""

    token: str

    def __post_init__(self) -> None:
        if self.token != SEALED_TEST_CONFIRMATION_TOKEN:
            raise PermissionError("sealed test requires an explicit confirmation token")
