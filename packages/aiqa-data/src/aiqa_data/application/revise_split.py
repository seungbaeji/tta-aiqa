"""Create a new benchmark split without reusing the parent sealed-test role."""

from __future__ import annotations

from aiqa_data.application.build_dataset import (
    PreparedPatientFeatures,
    PreparedSplitManifest,
)
from aiqa_data.domain import (
    BenchmarkSplitRevision,
    DatasetRole,
    SplitAssignment,
)
from aiqa_data.ports import RevisionPartitioner


class ReviseBenchmarkSplit:
    def __init__(self, partitioner: RevisionPartitioner) -> None:
        self._partitioner = partitioner

    def execute(
        self,
        *,
        features: PreparedPatientFeatures,
        parent: PreparedSplitManifest,
        revision: BenchmarkSplitRevision,
    ) -> PreparedSplitManifest:
        targets = {row.record_id: row.target for row in features.rows}
        parent_roles = {item.record_id: item.role for item in parent.splits}
        if set(parent_roles) != set(targets):
            raise ValueError("parent split must cover every patient exactly once")

        parent_test = sorted(
            record_id
            for record_id, role in parent_roles.items()
            if role is DatasetRole.TEST
        )
        if revision.parent_test_train_count >= len(parent_test):
            raise ValueError("revision must retain a non-empty operational pool")
        promoted, operational = self._partitioner.partition(
            record_ids=tuple(parent_test),
            targets=targets,
            train_count=revision.parent_test_train_count,
            random_seed=revision.random_seed,
        )
        promoted_ids = set(promoted)
        operational_ids = set(operational)

        assignments: list[SplitAssignment] = []
        for record_id, parent_role in sorted(parent_roles.items()):
            if parent_role is DatasetRole.TRAIN or record_id in promoted_ids:
                role = DatasetRole.TRAIN
            elif parent_role is DatasetRole.VALID:
                role = DatasetRole.VALID
            elif parent_role is DatasetRole.OPERATIONAL:
                role = DatasetRole.TEST
            elif record_id in operational_ids:
                role = DatasetRole.OPERATIONAL
            else:
                raise ValueError(f"unmapped parent split assignment: {record_id}")
            assignments.append(SplitAssignment(record_id=record_id, role=role))
        return PreparedSplitManifest(splits=tuple(assignments))
