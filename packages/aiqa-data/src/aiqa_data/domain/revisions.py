"""Benchmark split revision values and invariants."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkSplitRevision:
    """Immutable rules for creating a benchmark split revision."""

    revision: str
    parent_revision: str
    random_seed: int
    parent_test_train_count: int

    def __post_init__(self) -> None:
        if not self.revision or self.revision == self.parent_revision:
            raise ValueError("split revision must differ from its parent")
        if self.parent_test_train_count < 1:
            raise ValueError("promoted parent test count must be positive")
