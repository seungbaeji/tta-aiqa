"""Data preparation use cases independent from filesystem and sklearn adapters."""

from aiqa_data.application import (
    DatasetExpectations,
    build_patient_features,
    create_split_manifest,
    revise_benchmark_split,
)
from aiqa_data.domain import AggregationPlan, BenchmarkSplitRevision
from aiqa_data.ports import (
    OutcomeRepository,
    PatientRecordRepository,
    RevisionPartitioner,
    SplitStrategy,
)

from data_quality_pipeline.domain import (
    DataPreparationResult,
    DataQualityPaths,
    DataQualityStage,
)
from data_quality_pipeline.ports import DatasetArtifactStore, SourceGateway


def verify_source(
    paths: DataQualityPaths,
    *,
    source_gateway: SourceGateway,
) -> DataPreparationResult:
    """Verify official source integrity and write the typed source evidence artifact."""
    report = source_gateway.verify()
    source_gateway.write_evidence(report, paths.source_evidence_path)
    return DataPreparationResult(command=DataQualityStage.VERIFY_SOURCE)


def extract_source(
    _: DataQualityPaths,
    *,
    source_gateway: SourceGateway,
) -> DataPreparationResult:
    """Extract the official archive only through the verified source gateway."""
    source_gateway.extract()
    return DataPreparationResult(command=DataQualityStage.EXTRACT)


def aggregate_features(
    paths: DataQualityPaths,
    *,
    aggregation_plan: AggregationPlan,
    records: PatientRecordRepository,
    outcomes: OutcomeRepository,
    expectations: DatasetExpectations,
    artifacts: DatasetArtifactStore,
) -> DataPreparationResult:
    """Build patient-level features and persist the deterministic dataset artifact."""
    dataset = build_patient_features(
        aggregation_plan,
        records=records,
        outcomes=outcomes,
        expectations=expectations,
    )
    artifacts.write_features(dataset, paths.patient_features_path)
    return DataPreparationResult(
        command=DataQualityStage.AGGREGATE,
        rows=len(dataset.rows),
        features=len(dataset.feature_names),
    )


def create_split(
    paths: DataQualityPaths,
    *,
    splitter: SplitStrategy,
    artifacts: DatasetArtifactStore,
) -> DataPreparationResult:
    """Assign every feature row to one deterministic initial dataset role."""
    features = artifacts.read_features(paths.patient_features_path)
    manifest = create_split_manifest(features.rows, splitter=splitter)
    artifacts.write_split_manifest(manifest, paths.split_manifest_path)
    artifacts.write_role_datasets(features, manifest, paths.split_dataset_dir)
    return DataPreparationResult(
        command=DataQualityStage.SPLIT,
        rows=len(manifest.splits),
    )


def revise_split(
    paths: DataQualityPaths,
    *,
    revision: BenchmarkSplitRevision | None,
    partitioner: RevisionPartitioner,
    artifacts: DatasetArtifactStore,
) -> DataPreparationResult:
    """Create an approved benchmark split revision from the parent split only."""
    if revision is None:
        raise ValueError("split revision configuration is required")
    revision_paths = paths.split_revision_paths()
    features = artifacts.read_features(paths.patient_features_path)
    parent = artifacts.read_split_manifest(paths.split_manifest_path)
    manifest = revise_benchmark_split(
        features=features,
        parent=parent,
        revision=revision,
        partitioner=partitioner,
    )
    artifacts.write_split_manifest(manifest, revision_paths.manifest_path)
    artifacts.write_role_datasets(features, manifest, revision_paths.dataset_dir)
    return DataPreparationResult(
        command=DataQualityStage.REVISE_SPLIT,
        rows=len(manifest.splits),
    )
