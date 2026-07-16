"""Approved V2 benchmark split revision tests."""

from pathlib import Path

from aiqa_data.adapters import SklearnRevisionPartitioner, load_split_revision
from aiqa_data.application import (
    PreparedPatientFeatures,
    PreparedSplitManifest,
    revise_benchmark_split,
)
from aiqa_data.domain import DatasetRole, PatientFeatureRow, SplitAssignment


def test_revision_promotes_parent_test_and_seals_parent_operational() -> None:
    rows = tuple(
        PatientFeatureRow(
            record_id=record_id,
            target=record_id % 2,
            values=(("value", float(record_id)),),
        )
        for record_id in range(1, 25)
    )
    parent_roles = (
        [DatasetRole.TRAIN] * 10
        + [DatasetRole.VALID] * 4
        + [DatasetRole.TEST] * 8
        + [DatasetRole.OPERATIONAL] * 2
    )
    parent = PreparedSplitManifest(
        splits=tuple(
            SplitAssignment(record_id=index, role=role)
            for index, role in enumerate(parent_roles, start=1)
        )
    )
    revision = load_split_revision(Path("configs/data/split-revisions/v2.yaml"))
    revision = type(revision)(
        revision="test-v2",
        parent_revision="test-v1",
        random_seed=revision.random_seed,
        parent_test_train_count=6,
    )

    revised = revise_benchmark_split(
        features=PreparedPatientFeatures(feature_names=("value",), rows=rows),
        parent=parent,
        revision=revision,
        partitioner=SklearnRevisionPartitioner(),
    )

    roles = {item.record_id: item.role for item in revised.splits}
    counts = {role: list(roles.values()).count(role) for role in DatasetRole}
    assert counts == {
        DatasetRole.TRAIN: 16,
        DatasetRole.VALID: 4,
        DatasetRole.TEST: 2,
        DatasetRole.OPERATIONAL: 2,
    }
    assert all(roles[record_id] is DatasetRole.TEST for record_id in (23, 24))
    assert all(roles[record_id] is not DatasetRole.TEST for record_id in range(15, 23))


def test_v2_revision_contract_is_explicit_and_versioned() -> None:
    revision = load_split_revision(Path("configs/data/split-revisions/v2.yaml"))

    assert revision.revision == "v2"
    assert revision.parent_revision == "v1"
    assert revision.random_seed == 43
    assert revision.parent_test_train_count == 500
