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
    """Patient-level feature rows generated from source records."""

    feature_names: tuple[str, ...]
    rows: tuple[PatientFeatureRow, ...]


@dataclass(frozen=True)
class DatasetExpectations:
    """Source-contract counts checked while building patient features."""

    record_count: int
    positive_count: int


@dataclass(frozen=True)
class PreparedSplitManifest:
    """Deterministic role assignments for every prepared patient."""

    splits: tuple[SplitAssignment, ...]


@dataclass(frozen=True)
class PreparedPatientDataset:
    """Combined feature and role output used by data preparation clients."""

    feature_names: tuple[str, ...]
    rows: tuple[PatientFeatureRow, ...]
    splits: tuple[SplitAssignment, ...]


def build_patient_features(
    plan: AggregationPlan,
    *,
    records: PatientRecordRepository,
    outcomes: OutcomeRepository,
    expectations: DatasetExpectations | None = None,
) -> PreparedPatientFeatures:
    """Aggregate complete source records into deterministic patient features."""
    outcome_values = dict(outcomes.outcomes())
    rows: list[PatientFeatureRow] = []
    seen: set[int] = set()
    for record in records.records():
        if record.record_id in seen:
            raise ValueError(f"duplicate patient record: {record.record_id}")
        seen.add(record.record_id)
        if record.record_id not in outcome_values:
            raise ValueError(f"outcome missing for patient: {record.record_id}")
        rows.append(
            PatientFeatureRow(
                record_id=record.record_id,
                target=outcome_values[record.record_id],
                values=aggregate_record(record, plan),
            )
        )
    unmatched = set(outcome_values) - seen
    if unmatched:
        raise ValueError(f"patient records missing for outcomes: {len(unmatched)}")
    if expectations is not None:
        if len(rows) != expectations.record_count:
            raise ValueError("patient record count does not match source contract")
        if sum(row.target for row in rows) != expectations.positive_count:
            raise ValueError("positive target count does not match source contract")
    return PreparedPatientFeatures(
        feature_names=plan.feature_names,
        rows=tuple(sorted(rows, key=lambda row: row.record_id)),
    )


def create_split_manifest(
    rows: tuple[PatientFeatureRow, ...], *, splitter: SplitStrategy
) -> PreparedSplitManifest:
    """Assign exactly one configured dataset role to every feature row."""
    targets = {row.record_id: row.target for row in rows}
    splits = splitter.assign(targets)
    if {item.record_id for item in splits} != set(targets):
        raise ValueError("split assignments do not cover every patient")
    return PreparedSplitManifest(
        splits=tuple(sorted(splits, key=lambda item: item.record_id))
    )


def build_patient_dataset(
    plan: AggregationPlan,
    *,
    records: PatientRecordRepository,
    outcomes: OutcomeRepository,
    splitter: SplitStrategy,
    expectations: DatasetExpectations | None = None,
) -> PreparedPatientDataset:
    """Build patient features and their deterministic role assignments together."""
    features = build_patient_features(
        plan,
        records=records,
        outcomes=outcomes,
        expectations=expectations,
    )
    manifest = create_split_manifest(features.rows, splitter=splitter)
    return PreparedPatientDataset(
        feature_names=features.feature_names,
        rows=features.rows,
        splits=manifest.splits,
    )
