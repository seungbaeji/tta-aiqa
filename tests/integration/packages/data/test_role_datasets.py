"""Physical role dataset boundary tests."""

import csv
from pathlib import Path

from aiqa_data.adapters import write_role_datasets
from aiqa_data.application import PreparedPatientFeatures, PreparedSplitManifest
from aiqa_data.domain import DatasetRole, PatientFeatureRow, SplitAssignment


def test_role_datasets_seal_test_and_remove_operational_target(
    tmp_path: Path,
) -> None:
    features = PreparedPatientFeatures(
        feature_names=("heart_rate",),
        rows=tuple(
            PatientFeatureRow(
                record_id=record_id,
                target=record_id % 2,
                values=(("heart_rate", float(60 + record_id)),),
            )
            for record_id in range(1, 5)
        ),
    )
    manifest = PreparedSplitManifest(
        splits=tuple(
            SplitAssignment(record_id=index, role=role)
            for index, role in enumerate(DatasetRole, start=1)
        )
    )

    write_role_datasets(features, manifest, tmp_path)

    for role in DatasetRole:
        with (tmp_path / f"{role.value}.csv").open(
            newline="", encoding="utf-8"
        ) as file:
            header = next(csv.reader(file))
        assert ("target" in header) is (role is not DatasetRole.OPERATIONAL)
