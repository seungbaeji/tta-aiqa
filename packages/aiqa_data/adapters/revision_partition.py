"""Sklearn stratified benchmark revision partitioner."""

from sklearn.model_selection import train_test_split


class SklearnRevisionPartitioner:
    """Use sklearn stratification to partition a parent sealed-test cohort."""

    def partition(
        self,
        *,
        record_ids: tuple[int, ...],
        targets: dict[int, int],
        train_count: int,
        random_seed: int,
    ) -> tuple[tuple[int, ...], tuple[int, ...]]:
        """Return deterministic promoted-train and retained-operational IDs."""
        promoted, operational = train_test_split(
            record_ids,
            train_size=train_count,
            random_state=random_seed,
            stratify=[targets[record_id] for record_id in record_ids],
        )
        return tuple(sorted(promoted)), tuple(sorted(operational))
