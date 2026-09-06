"""Benchmark split revision sampling port."""

from typing import Protocol


class RevisionPartitioner(Protocol):
    """Partition a parent sealed cohort for a new benchmark revision."""

    def partition(
        self,
        *,
        record_ids: tuple[int, ...],
        targets: dict[int, int],
        train_count: int,
        random_seed: int,
    ) -> tuple[tuple[int, ...], tuple[int, ...]]:
        """Return promoted-train and retained-operational record IDs."""
        ...
