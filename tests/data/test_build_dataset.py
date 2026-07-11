"""Patient dataset application tests with in-memory ports."""

from collections.abc import Iterable, Mapping

import pytest
from aiqa_data.application import BuildPatientDataset
from aiqa_data.domain import (
    AggregationPlan,
    DatasetRole,
    Observation,
    PatientRecord,
    SplitAssignment,
    StaticFeatureRule,
)


class Records:
    def __init__(self, values: tuple[PatientRecord, ...]) -> None:
        self._values = values

    def records(self) -> Iterable[PatientRecord]:
        return self._values


class Outcomes:
    def __init__(self, values: Mapping[int, int]) -> None:
        self._values = values

    def outcomes(self) -> Mapping[int, int]:
        return self._values


class Splits:
    def assign(self, targets: Mapping[int, int]) -> tuple[SplitAssignment, ...]:
        return tuple(
            SplitAssignment(record_id, DatasetRole.TRAIN) for record_id in targets
        )


PLAN = AggregationPlan(
    missing_sentinel=-1.0,
    static_features=(StaticFeatureRule("Age", "age"),),
    series_features=(),
)


def test_use_case_joins_outcome_and_assigns_every_patient() -> None:
    use_case = BuildPatientDataset(
        Records((PatientRecord(7, (Observation(0, "Age", 44),)),)),
        Outcomes({7: 1}),
        Splits(),
    )

    result = use_case.execute(PLAN)

    assert result.feature_names == ("age", "age__missing")
    assert result.rows[0].as_mapping() == {
        "record_id": 7,
        "age": 44,
        "age__missing": 0.0,
        "target": 1,
    }
    assert result.splits == (SplitAssignment(7, DatasetRole.TRAIN),)


def test_use_case_rejects_incomplete_outcome_join() -> None:
    use_case = BuildPatientDataset(
        Records((PatientRecord(7, ()),)), Outcomes({8: 0}), Splits()
    )

    with pytest.raises(ValueError, match="outcome missing"):
        use_case.execute(PLAN)
