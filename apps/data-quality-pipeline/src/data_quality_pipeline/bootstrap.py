"""Composition root for the Data Quality Pipeline process."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

from aiqa_data.adapters import (
    PhysioNetOutcomeRepository,
    PhysioNetRecordRepository,
    SklearnRevisionPartitioner,
    SklearnStratifiedSplitStrategy,
    load_aggregation_plan,
    load_source_contract,
    load_split_config,
    load_split_revision,
)
from aiqa_data.application import DatasetExpectations
from aiqa_observability import Telemetry, create_telemetry, load_telemetry_policy

from data_quality_pipeline.adapters import (
    CsvDatasetArtifactStore,
    GreatExpectationsQualityValidator,
    PhysioNetSourceGateway,
)
from data_quality_pipeline.adapters.quality import load_quality_rules
from data_quality_pipeline.application.commands import (
    DataQualityOperations,
    execute_data_quality_stage,
)
from data_quality_pipeline.application.preparation import (
    aggregate_features,
    create_split,
    extract_source,
    revise_split,
    verify_source,
)
from data_quality_pipeline.application.validation import validate_quality
from data_quality_pipeline.domain import DataPreparationResult, DataQualityStage
from data_quality_pipeline.settings import DataQualitySettings


@dataclass(frozen=True)
class DataQualityRuntime:
    """Bound data-quality stage operation and telemetry for one process."""

    run: Callable[[DataQualityStage], DataPreparationResult]
    telemetry: Telemetry


def bootstrap(settings: DataQualitySettings) -> DataQualityRuntime:
    """Assemble concrete data, source, and quality adapters for one process run."""
    paths = settings.to_paths()
    source = load_source_contract(paths.source_contract_path)
    aggregation_plan = load_aggregation_plan(paths.aggregation_config_path)
    records = PhysioNetRecordRepository(
        source.records_dir,
        source.expected_record_count,
        source.observation_window_hours,
    )
    outcomes = PhysioNetOutcomeRepository(
        source.outcomes_path,
        target_column=source.target_column,
        blocked_columns=source.blocked_outcome_columns,
    )
    artifacts = CsvDatasetArtifactStore()
    source_gateway = PhysioNetSourceGateway(source)
    revision = (
        load_split_revision(paths.split_revision_config_path)
        if paths.split_revision_config_path is not None
        else None
    )
    validator = (
        GreatExpectationsQualityValidator(
            records=records,
            aggregation_plan=aggregation_plan,
            rules=load_quality_rules(paths.quality_rules_path),
        )
        if paths.quality_rules_path is not None
        else None
    )
    operations = DataQualityOperations(
        verify_source=partial(
            verify_source,
            paths,
            source_gateway=source_gateway,
        ),
        extract=partial(
            extract_source,
            paths,
            source_gateway=source_gateway,
        ),
        aggregate=partial(
            aggregate_features,
            paths,
            aggregation_plan=aggregation_plan,
            records=records,
            outcomes=outcomes,
            expectations=DatasetExpectations(
                record_count=source.expected_record_count,
                positive_count=source.expected_death_count,
            ),
            artifacts=artifacts,
        ),
        split=partial(
            create_split,
            paths,
            splitter=SklearnStratifiedSplitStrategy(
                load_split_config(paths.split_config_path)
            ),
            artifacts=artifacts,
        ),
        revise_split=partial(
            revise_split,
            paths,
            revision=revision,
            partitioner=SklearnRevisionPartitioner(),
            artifacts=artifacts,
        ),
        validate=partial(
            validate_quality,
            paths,
            validator=validator,
        ),
    )
    return DataQualityRuntime(
        run=partial(execute_data_quality_stage, operations=operations),
        telemetry=create_telemetry(
            service_name="data-quality-pipeline",
            environment=settings.environment,
            policy=load_telemetry_policy(settings.telemetry_config_path),
            otlp_endpoint=(
                str(settings.otlp_endpoint) if settings.otlp_endpoint else None
            ),
        ),
    )
