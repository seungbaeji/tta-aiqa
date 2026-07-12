"""Composition root for the Data Quality Pipeline."""

from collections.abc import Callable
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
    DatasetExpectations,
    build_patient_features,
    create_split_manifest,
    revise_benchmark_split,
)
from aiqa_observability import Telemetry, create_telemetry, load_telemetry_policy

from data_quality_pipeline.settings import DataQualitySettings
from data_quality_pipeline.validation import validate
from data_quality_pipeline.workflow import (
    DataPreparationResult,
    DataQualityPaths,
    DataQualityStage,
)


@dataclass(frozen=True)
class DataQualityRuntime:
    """Bound data-quality stage operation and telemetry for one process."""

    run: Callable[[DataQualityStage], DataPreparationResult]
    telemetry: Telemetry


def bootstrap(settings: DataQualitySettings) -> DataQualityRuntime:
    """Assemble filesystem adapters and telemetry for one workflow invocation."""
    paths = settings.to_paths()

    def run(stage: DataQualityStage) -> DataPreparationResult:
        return _run_stage(stage, paths)

    return DataQualityRuntime(
        run=run,
        telemetry=create_telemetry(
            service_name="data-quality-pipeline",
            environment=settings.environment,
            policy=load_telemetry_policy(settings.telemetry_config_path),
            otlp_endpoint=(
                str(settings.otlp_endpoint) if settings.otlp_endpoint else None
            ),
        ),
    )


def _run_stage(
    stage: DataQualityStage, paths: DataQualityPaths
) -> DataPreparationResult:
    if stage is DataQualityStage.VERIFY_SOURCE:
        return _verify_source(paths)
    if stage is DataQualityStage.EXTRACT:
        return _extract_source(paths)
    if stage is DataQualityStage.AGGREGATE:
        return _aggregate(paths)
    if stage is DataQualityStage.SPLIT:
        return _split(paths)
    if stage is DataQualityStage.REVISE_SPLIT:
        return _revise_split(paths)
    if stage is DataQualityStage.VALIDATE:
        return validate(paths)
    raise ValueError(f"unsupported data-quality stage: {stage}")


def _verify_source(paths: DataQualityPaths) -> DataPreparationResult:
    source = load_source_contract(paths.source_contract_path)
    evidence = verify_source_manifest(source.source_manifest_path)
    write_json(evidence, paths.source_evidence_path)
    return DataPreparationResult(command=DataQualityStage.VERIFY_SOURCE)


def _extract_source(paths: DataQualityPaths) -> DataPreparationResult:
    source = load_source_contract(paths.source_contract_path)
    manifest = verify_source_manifest(source.source_manifest_path)
    archive_name = next(
        item["path"] for item in manifest["files"] if item["path"] == "set-a.zip"
    )
    extract_archive(
        source.source_manifest_path.parent / str(archive_name),
        source.records_dir.parent,
    )
    return DataPreparationResult(command=DataQualityStage.EXTRACT)


def _aggregate(paths: DataQualityPaths) -> DataPreparationResult:
    source = load_source_contract(paths.source_contract_path)
    verify_source_manifest(source.source_manifest_path)
    plan = load_aggregation_plan(paths.aggregation_config_path)
    dataset = build_patient_features(
        plan,
        records=PhysioNetRecordRepository(
            source.records_dir,
            source.expected_record_count,
            source.observation_window_hours,
        ),
        outcomes=PhysioNetOutcomeRepository(
            source.outcomes_path,
            target_column=source.target_column,
            blocked_columns=source.blocked_outcome_columns,
        ),
        expectations=DatasetExpectations(
            record_count=source.expected_record_count,
            positive_count=source.expected_death_count,
        ),
    )
    write_dataset_csv(dataset, paths.patient_features_path)
    return DataPreparationResult(
        command=DataQualityStage.AGGREGATE,
        rows=len(dataset.rows),
        features=len(dataset.feature_names),
    )


def _split(paths: DataQualityPaths) -> DataPreparationResult:
    features = read_dataset_csv(paths.patient_features_path)
    manifest = create_split_manifest(
        features.rows,
        splitter=SklearnStratifiedSplitStrategy(load_split_config(paths.split_config_path)),
    )
    write_split_csv(manifest, paths.split_manifest_path)
    write_role_datasets(features, manifest, paths.split_dataset_dir)
    return DataPreparationResult(
        command=DataQualityStage.SPLIT, rows=len(manifest.splits)
    )


def _revise_split(paths: DataQualityPaths) -> DataPreparationResult:
    if (
        paths.split_revision_config_path is None
        or paths.revision_split_manifest_path is None
        or paths.revision_split_dataset_dir is None
    ):
        raise ValueError("split revision paths are required")
    features = read_dataset_csv(paths.patient_features_path)
    parent = read_split_csv(paths.split_manifest_path)
    revision = load_split_revision(paths.split_revision_config_path)
    manifest = revise_benchmark_split(
        features=features,
        parent=parent,
        revision=revision,
        partitioner=SklearnRevisionPartitioner(),
    )
    write_split_csv(manifest, paths.revision_split_manifest_path)
    write_role_datasets(features, manifest, paths.revision_split_dataset_dir)
    return DataPreparationResult(
        command=DataQualityStage.REVISE_SPLIT, rows=len(manifest.splits)
    )
