"""Build a leakage-safe patient-level feature dataset."""

from __future__ import annotations

from dataclasses import dataclass

from aiqa_data.domain import (
    AggregationPlan,
    PatientFeatureRow,
    SplitAssignment,
    aggregate_record,
)
from aiqa_data.ports import OutcomeRepository, PatientRecordRepository, SplitStrategy


@dataclass(frozen=True)
class PreparedPatientFeatures:
    feature_names: tuple[str, ...]
    rows: tuple[PatientFeatureRow, ...]


@dataclass(frozen=True)
class DatasetExpectations:
    record_count: int
    positive_count: int


@dataclass(frozen=True)
class PreparedSplitManifest:
    splits: tuple[SplitAssignment, ...]


@dataclass(frozen=True)
class PreparedPatientDataset:
    feature_names: tuple[str, ...]
    rows: tuple[PatientFeatureRow, ...]
    splits: tuple[SplitAssignment, ...]


class BuildPatientFeatures:
    def __init__(
        self,
        records: PatientRecordRepository,
        outcomes: OutcomeRepository,
        expectations: DatasetExpectations | None = None,
    ) -> None:
        self._records = records
        self._outcomes = outcomes
        self._expectations = expectations

    def execute(self, plan: AggregationPlan) -> PreparedPatientFeatures:
        outcomes = dict(self._outcomes.outcomes())
        rows: list[PatientFeatureRow] = []
        seen: set[int] = set()
        for record in self._records.records():
            if record.record_id in seen:
                raise ValueError(f"duplicate patient record: {record.record_id}")
            seen.add(record.record_id)
            if record.record_id not in outcomes:
                raise ValueError(f"outcome missing for patient: {record.record_id}")
            rows.append(
                PatientFeatureRow(
                    record_id=record.record_id,
                    target=outcomes[record.record_id],
                    values=aggregate_record(record, plan),
                )
            )
        unmatched = set(outcomes) - seen
        if unmatched:
            raise ValueError(f"patient records missing for outcomes: {len(unmatched)}")
        if self._expectations is not None:
            if len(rows) != self._expectations.record_count:
                raise ValueError("patient record count does not match source contract")
            if sum(row.target for row in rows) != self._expectations.positive_count:
                raise ValueError("positive target count does not match source contract")
        return PreparedPatientFeatures(
            feature_names=plan.feature_names,
            rows=tuple(sorted(rows, key=lambda row: row.record_id)),
        )


class CreateSplitManifest:
    def __init__(self, splitter: SplitStrategy) -> None:
        self._splitter = splitter

    def execute(self, rows: tuple[PatientFeatureRow, ...]) -> PreparedSplitManifest:
        targets = {row.record_id: row.target for row in rows}
        splits = self._splitter.assign(targets)
        if {item.record_id for item in splits} != set(targets):
            raise ValueError("split assignments do not cover every patient")
        return PreparedSplitManifest(
            splits=tuple(sorted(splits, key=lambda item: item.record_id))
        )


class BuildPatientDataset:
    def __init__(
        self,
        records: PatientRecordRepository,
        outcomes: OutcomeRepository,
        splitter: SplitStrategy,
        expectations: DatasetExpectations | None = None,
    ) -> None:
        self._feature_builder = BuildPatientFeatures(records, outcomes, expectations)
        self._split_builder = CreateSplitManifest(splitter)

    def execute(self, plan: AggregationPlan) -> PreparedPatientDataset:
        features = self._feature_builder.execute(plan)
        manifest = self._split_builder.execute(features.rows)
        return PreparedPatientDataset(
            feature_names=features.feature_names,
            rows=features.rows,
            splits=manifest.splits,
        )
