"""Data Quality Pipeline application behavior with explicit fake ports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from aiqa_data.application import PreparedPatientFeatures, PreparedSplitManifest
from aiqa_data.domain import (
    AggregationPlan,
    BenchmarkSplitRevision,
    DatasetRole,
    Observation,
    PatientFeatureRow,
    PatientRecord,
    SourceDatasetIdentity,
    SourceIntegrityReport,
    SourceLicenseReference,
    SplitAssignment,
    StaticFeatureRule,
    VerifiedSourceFile,
)
from data_quality_pipeline.application.commands import (
    DataQualityOperations,
    execute_data_quality_stage,
)
from data_quality_pipeline.application.preparation import (
    aggregate_features,
    create_split,
    revise_split,
    verify_source,
)
from data_quality_pipeline.application.validation import validate_quality
from data_quality_pipeline.domain import (
    DataPreparationResult,
    DataQualityPaths,
    DataQualityStage,
)


def paths(tmp_path: Path, *, include_revision: bool = False) -> DataQualityPaths:
    """Return deterministic artifact locations for one application test."""
    revision_paths = (
        {
            "split_revision_config_path": tmp_path / "revision.yaml",
            "revision_split_manifest_path": tmp_path / "revisions/manifest.csv",
            "revision_split_dataset_dir": tmp_path / "revisions/datasets",
        }
        if include_revision
        else {}
    )
    return DataQualityPaths(
        source_contract_path=tmp_path / "source.yaml",
        aggregation_config_path=tmp_path / "aggregation.yaml",
        split_config_path=tmp_path / "split.yaml",
        patient_features_path=tmp_path / "patient-features.csv",
        split_manifest_path=tmp_path / "split-manifest.csv",
        split_dataset_dir=tmp_path / "datasets",
        source_evidence_path=tmp_path / "source-integrity.json",
        quality_rules_path=tmp_path / "quality-rules.yaml",
        validation_artifact_dir=tmp_path / "validation",
        **revision_paths,
    )


def source_report() -> SourceIntegrityReport:
    """Return minimal typed source integrity evidence for a gateway fake."""
    return SourceIntegrityReport(
        schema_version=1,
        dataset=SourceDatasetIdentity(
            name="PhysioNet Challenge",
            challenge="2012",
            version="1",
            subset="set-a",
            homepage="https://example.test/source",
            retrieved_on=date(2026, 1, 1),
        ),
        license=SourceLicenseReference(
            name="License",
            identifier="license",
            url="https://example.test/license",
        ),
        files=(
            VerifiedSourceFile(
                path="set-a.zip",
                size_bytes=1,
                sha256="a" * 64,
            ),
        ),
    )


def patient_features() -> PreparedPatientFeatures:
    """Return two patient rows sufficient to exercise app artifact orchestration."""
    return PreparedPatientFeatures(
        feature_names=("age", "age__missing"),
        rows=(
            PatientFeatureRow(
                record_id=1,
                target=0,
                values=(("age", 50.0), ("age__missing", 0.0)),
            ),
            PatientFeatureRow(
                record_id=2,
                target=1,
                values=(("age", 60.0), ("age__missing", 0.0)),
            ),
            PatientFeatureRow(
                record_id=3,
                target=0,
                values=(("age", 70.0), ("age__missing", 0.0)),
            ),
            PatientFeatureRow(
                record_id=4,
                target=1,
                values=(("age", 80.0), ("age__missing", 0.0)),
            ),
            PatientFeatureRow(
                record_id=5,
                target=0,
                values=(("age", 90.0), ("age__missing", 0.0)),
            ),
        ),
    )


@dataclass
class SourceGatewaySpy:
    """Capture source evidence writes without filesystem or archive dependencies."""

    report: SourceIntegrityReport
    evidence_writes: list[tuple[SourceIntegrityReport, Path]] = field(
        default_factory=list
    )

    def verify(self) -> SourceIntegrityReport:
        """Return the configured typed integrity report."""
        return self.report

    def write_evidence(self, report: SourceIntegrityReport, path: Path) -> None:
        """Capture the report and evidence destination requested by the use case."""
        self.evidence_writes.append((report, path))

    def extract(self) -> None:
        """Satisfy the source gateway contract outside this test's scope."""


@dataclass
class ArtifactStoreSpy:
    """Capture deterministic dataset artifact reads and writes in memory."""

    features: PreparedPatientFeatures
    manifest: PreparedSplitManifest | None = None
    feature_writes: list[tuple[PreparedPatientFeatures, Path]] = field(
        default_factory=list
    )
    manifest_writes: list[tuple[PreparedSplitManifest, Path]] = field(
        default_factory=list
    )
    role_dataset_writes: list[
        tuple[PreparedPatientFeatures, PreparedSplitManifest, Path]
    ] = field(default_factory=list)

    def read_features(self, _: Path) -> PreparedPatientFeatures:
        """Return the configured patient features."""
        return self.features

    def read_split_manifest(self, _: Path) -> PreparedSplitManifest:
        """Return the configured parent split manifest."""
        assert self.manifest is not None
        return self.manifest

    def write_features(self, dataset: PreparedPatientFeatures, path: Path) -> None:
        """Capture the feature artifact requested by the use case."""
        self.feature_writes.append((dataset, path))

    def write_split_manifest(
        self,
        manifest: PreparedSplitManifest,
        path: Path,
    ) -> None:
        """Capture the split manifest artifact requested by the use case."""
        self.manifest_writes.append((manifest, path))

    def write_role_datasets(
        self,
        features: PreparedPatientFeatures,
        manifest: PreparedSplitManifest,
        output_dir: Path,
    ) -> None:
        """Capture role-dataset persistence requested by the use case."""
        self.role_dataset_writes.append((features, manifest, output_dir))


@dataclass(frozen=True)
class FixedSplitStrategy:
    """Assign the fixture patients to each initial dataset role deterministically."""

    def assign(self, _: dict[int, int]) -> tuple[SplitAssignment, ...]:
        """Return a complete fixture assignment for all patient IDs."""
        return (
            SplitAssignment(record_id=1, role=DatasetRole.TRAIN),
            SplitAssignment(record_id=2, role=DatasetRole.VALID),
            SplitAssignment(record_id=3, role=DatasetRole.TEST),
            SplitAssignment(record_id=4, role=DatasetRole.TEST),
            SplitAssignment(record_id=5, role=DatasetRole.OPERATIONAL),
        )


@dataclass(frozen=True)
class FixedRevisionPartitioner:
    """Promote one former sealed-test patient for the approved revision."""

    def partition(
        self,
        *,
        record_ids: tuple[int, ...],
        targets: dict[int, int],
        train_count: int,
        random_seed: int,
    ) -> tuple[tuple[int, ...], tuple[int, ...]]:
        """Return the fixture promotion while asserting application inputs."""
        assert record_ids == (3, 4)
        assert targets == {1: 0, 2: 1, 3: 0, 4: 1, 5: 0}
        assert train_count == 1
        assert random_seed == 43
        return (3,), (4,)


@dataclass(frozen=True)
class QualityValidatorSpy:
    """Return a configured GE result without invoking the adapter runtime."""

    success: bool

    def validate(self, patient_features_path: Path, artifact_dir: Path) -> bool:
        """Return the configured validation state after checking its two paths."""
        assert patient_features_path.name == "patient-features.csv"
        assert artifact_dir.name == "validation"
        return self.success


@dataclass(frozen=True)
class PatientRecords:
    """Supply a single raw patient record to aggregation behavior tests."""

    def records(self) -> tuple[PatientRecord, ...]:
        """Return the one configured raw patient record."""
        return (
            PatientRecord(
                record_id=1,
                observations=(
                    Observation(minute=0, parameter="Age", value=50.0),
                ),
            ),
        )


@dataclass(frozen=True)
class PatientOutcomes:
    """Supply the target associated with the aggregation fixture record."""

    def outcomes(self) -> dict[int, int]:
        """Return the fixture outcome by patient record ID."""
        return {1: 1}


def test_verify_source_writes_typed_evidence_to_the_configured_artifact(
    tmp_path: Path,
) -> None:
    """Source verification delegates evidence persistence through the outbound port."""
    configured_paths = paths(tmp_path)
    gateway = SourceGatewaySpy(report=source_report())

    result = verify_source(configured_paths, source_gateway=gateway)

    assert result == DataPreparationResult(command=DataQualityStage.VERIFY_SOURCE)
    assert gateway.evidence_writes == [
        (gateway.report, configured_paths.source_evidence_path)
    ]


def test_aggregate_features_persists_the_canonical_dataset_artifact(
    tmp_path: Path,
) -> None:
    """Aggregation owns data orchestration while its artifact port owns persistence."""
    configured_paths = paths(tmp_path)
    artifacts = ArtifactStoreSpy(features=patient_features())

    result = aggregate_features(
        configured_paths,
        aggregation_plan=AggregationPlan(
            missing_sentinel=-1.0,
            static_features=(StaticFeatureRule(parameter="Age", output_name="age"),),
            series_features=(),
        ),
        records=PatientRecords(),
        outcomes=PatientOutcomes(),
        expectations=None,
        artifacts=artifacts,
    )

    assert result == DataPreparationResult(
        command=DataQualityStage.AGGREGATE,
        rows=1,
        features=2,
    )
    assert artifacts.feature_writes[0][1] == configured_paths.patient_features_path
    assert artifacts.feature_writes[0][0].rows[0].record_id == 1


def test_split_and_revision_write_their_distinct_artifact_locations(
    tmp_path: Path,
) -> None:
    """Initial and revision split use cases never share their output destinations."""
    configured_paths = paths(tmp_path, include_revision=True)
    initial_store = ArtifactStoreSpy(features=patient_features())

    initial = create_split(
        configured_paths,
        splitter=FixedSplitStrategy(),
        artifacts=initial_store,
    )
    parent = initial_store.manifest_writes[0][0]
    revision_store = ArtifactStoreSpy(features=patient_features(), manifest=parent)
    revision = revise_split(
        configured_paths,
        revision=BenchmarkSplitRevision(
            revision="v2",
            parent_revision="v1",
            random_seed=43,
            parent_test_train_count=1,
        ),
        partitioner=FixedRevisionPartitioner(),
        artifacts=revision_store,
    )

    assert initial == DataPreparationResult(command=DataQualityStage.SPLIT, rows=5)
    assert revision == DataPreparationResult(
        command=DataQualityStage.REVISE_SPLIT,
        rows=5,
    )
    assert initial_store.manifest_writes[0][1] == configured_paths.split_manifest_path
    assert revision_store.manifest_writes[0][1] == (
        configured_paths.revision_split_manifest_path
    )
    assert revision_store.role_dataset_writes[0][2] == (
        configured_paths.revision_split_dataset_dir
    )


def test_validation_returns_failed_evidence_without_becoming_a_publish_gate(
    tmp_path: Path,
) -> None:
    """A failed GE result is observable to delivery without mutating data artifacts."""
    result = validate_quality(
        paths(tmp_path),
        validator=QualityValidatorSpy(success=False),
    )

    assert result == DataPreparationResult(
        command=DataQualityStage.VALIDATE,
        success=False,
    )


def test_stage_dispatch_invokes_only_the_named_bound_use_case() -> None:
    """Delivery dispatch remains explicit after bootstrap binds each operation."""
    invoked: list[DataQualityStage] = []

    def operation(stage: DataQualityStage) -> DataPreparationResult:
        """Record one selected operation and return its typed stage outcome."""
        invoked.append(stage)
        return DataPreparationResult(command=stage)

    operations = DataQualityOperations(
        verify_source=lambda: operation(DataQualityStage.VERIFY_SOURCE),
        extract=lambda: operation(DataQualityStage.EXTRACT),
        aggregate=lambda: operation(DataQualityStage.AGGREGATE),
        split=lambda: operation(DataQualityStage.SPLIT),
        revise_split=lambda: operation(DataQualityStage.REVISE_SPLIT),
        validate=lambda: operation(DataQualityStage.VALIDATE),
    )

    result = execute_data_quality_stage(
        DataQualityStage.REVISE_SPLIT,
        operations=operations,
    )

    assert result == DataPreparationResult(command=DataQualityStage.REVISE_SPLIT)
    assert invoked == [DataQualityStage.REVISE_SPLIT]
