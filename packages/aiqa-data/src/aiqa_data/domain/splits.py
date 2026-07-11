"""Patient-level dataset split values."""

from dataclasses import dataclass
from enum import StrEnum


class DatasetRole(StrEnum):
    TRAIN = "train"
    VALID = "valid"
    TEST = "test"
    OPERATIONAL = "operational"


@dataclass(frozen=True)
class SplitAssignment:
    record_id: int
    role: DatasetRole
