"""Patient-level dataset split values."""

from dataclasses import dataclass
from enum import StrEnum


class DatasetRole(StrEnum):
    """Named dataset roles with explicit training and sealing semantics."""

    TRAIN = "train"
    VALID = "valid"
    TEST = "test"
    OPERATIONAL = "operational"


@dataclass(frozen=True)
class SplitAssignment:
    """Assign one patient record to exactly one dataset role."""

    record_id: int
    role: DatasetRole
