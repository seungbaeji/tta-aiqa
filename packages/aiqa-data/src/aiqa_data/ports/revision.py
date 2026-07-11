"""Benchmark split revision sampling port."""

from typing import Protocol


class RevisionPartitioner(Protocol):
    def partition(
        self,
        *,
        record_ids: tuple[int, ...],
        targets: dict[int, int],
        train_count: int,
        random_seed: int,
    ) -> tuple[tuple[int, ...], tuple[int, ...]]: ...
