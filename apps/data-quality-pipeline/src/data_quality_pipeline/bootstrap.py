"""Composition root for the Data Quality Pipeline."""

from dataclasses import dataclass

from aiqa_data.adapters import (
    PhysioNetOutcomeRepository,
    PhysioNetRecordRepository,
    SklearnRevisionPartitioner,
    SklearnStratifiedSplitStrategy,
    extract_archive,
    load_aggregation_plan,
    load_source_contract,
    load_split_config,
    load_split_revision,
    read_dataset_csv,
    read_split_csv,
    verify_source_manifest,
    write_dataset_csv,
    write_json,
    write_role_datasets,
    write_split_csv,
)
from aiqa_data.application import (
    BuildPatientFeatures,
    CreateSplitManifest,
    DatasetExpectations,
    ReviseBenchmarkSplit,
)

from data_quality_pipeline.settings import DataQualitySettings


@dataclass(frozen=True)
class DataPreparationResult:
    command: str
    rows: int | None = None
    features: int | None = None
    success: bool | None = None


def verify_source(settings: DataQualitySettings) -> DataPreparationResult:
    source = load_source_contract(settings.source_contract_path)
    evidence = verify_source_manifest(source.source_manifest_path)
    write_json(evidence, settings.source_evidence_path)
    return DataPreparationResult(command="verify-source")


def extract_source(settings: DataQualitySettings) -> DataPreparationResult:
    source = load_source_contract(settings.source_contract_path)
    manifest = verify_source_manifest(source.source_manifest_path)
    archive_name = next(
        item["path"] for item in manifest["files"] if item["path"] == "set-a.zip"
    )
    extract_archive(
        source.source_manifest_path.parent / str(archive_name),
        source.records_dir.parent,
    )
    return DataPreparationResult(command="extract")


def aggregate(settings: DataQualitySettings) -> DataPreparationResult:
    source = load_source_contract(settings.source_contract_path)
    verify_source_manifest(source.source_manifest_path)
    plan = load_aggregation_plan(settings.aggregation_config_path)
    use_case = BuildPatientFeatures(
        PhysioNetRecordRepository(
            source.records_dir,
            source.expected_record_count,
            source.observation_window_hours,
        ),
        PhysioNetOutcomeRepository(
            source.outcomes_path,
            target_column=source.target_column,
            blocked_columns=source.blocked_outcome_columns,
        ),
        DatasetExpectations(
            record_count=source.expected_record_count,
            positive_count=source.expected_death_count,
        ),
    )
    dataset = use_case.execute(plan)
    write_dataset_csv(dataset, settings.patient_features_path)
    return DataPreparationResult(
        command="aggregate", rows=len(dataset.rows), features=len(dataset.feature_names)
    )


def split(settings: DataQualitySettings) -> DataPreparationResult:
    features = read_dataset_csv(settings.patient_features_path)
    strategy = SklearnStratifiedSplitStrategy(
        load_split_config(settings.split_config_path)
    )
    manifest = CreateSplitManifest(strategy).execute(features.rows)
    write_split_csv(manifest, settings.split_manifest_path)
    write_role_datasets(features, manifest, settings.split_dataset_dir)
    return DataPreparationResult(command="split", rows=len(manifest.splits))


def revise_split(settings: DataQualitySettings) -> DataPreparationResult:
    if (
        settings.split_revision_config_path is None
        or settings.revision_split_manifest_path is None
        or settings.revision_split_dataset_dir is None
    ):
        raise ValueError("split revision paths are required")
    features = read_dataset_csv(settings.patient_features_path)
    parent = read_split_csv(settings.split_manifest_path)
    revision = load_split_revision(settings.split_revision_config_path)
    manifest = ReviseBenchmarkSplit(SklearnRevisionPartitioner()).execute(
        features=features,
        parent=parent,
        revision=revision,
    )
    write_split_csv(manifest, settings.revision_split_manifest_path)
    write_role_datasets(features, manifest, settings.revision_split_dataset_dir)
    return DataPreparationResult(command="revise-split", rows=len(manifest.splits))
