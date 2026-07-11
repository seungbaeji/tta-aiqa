"""Composition for GE validation, intentionally separate from DVC preparation."""

from dataclasses import asdict

import pandas as pd
from aiqa_data.adapters import (
    PhysioNetRecordRepository,
    load_aggregation_plan,
    load_source_contract,
    write_json,
)
from aiqa_data.application import profile_raw_records

from data_quality_pipeline.adapters.expectations import (
    processed_expectations,
    raw_expectations,
)
from data_quality_pipeline.adapters.great_expectations import run_checkpoint
from data_quality_pipeline.adapters.quality import load_quality_rules
from data_quality_pipeline.bootstrap import DataPreparationResult
from data_quality_pipeline.settings import DataQualitySettings


def validate(settings: DataQualitySettings) -> DataPreparationResult:
    if settings.quality_rules_path is None or settings.validation_artifact_dir is None:
        raise ValueError(
            "validate requires quality rules and validation artifact paths"
        )
    source = load_source_contract(settings.source_contract_path)
    plan = load_aggregation_plan(settings.aggregation_config_path)
    rules = load_quality_rules(settings.quality_rules_path)
    records = PhysioNetRecordRepository(
        source.records_dir,
        source.expected_record_count,
        source.observation_window_hours,
    )
    raw_frame = pd.DataFrame(
        asdict(item) for item in profile_raw_records(records, plan.missing_sentinel)
    )
    processed_frame = pd.read_csv(settings.patient_features_path)
    raw_result = run_checkpoint(
        raw_frame,
        name="raw-ingestion",
        expectations=raw_expectations(rules),
        project_root=settings.validation_artifact_dir / "raw",
    )
    processed_result = run_checkpoint(
        processed_frame,
        name="processed-readiness",
        expectations=processed_expectations(rules, plan.feature_names),
        project_root=settings.validation_artifact_dir / "processed",
    )
    success = bool(raw_result["success"] and processed_result["success"])
    missing_columns = [
        column for column in processed_frame.columns if column.endswith("__missing")
    ]
    missing_rates = {
        column.removesuffix("__missing"): float(processed_frame[column].mean())
        for column in missing_columns
    }
    write_json(
        {
            "schema_version": 1,
            "success": success,
            "raw_ingestion": raw_result,
            "processed_readiness": processed_result,
            "profile": {
                "raw": {
                    "records": len(raw_frame),
                    "observations": int(raw_frame["observation_count"].sum()),
                    "sentinels": int(raw_frame["sentinel_count"].sum()),
                    "maximum_minute": int(raw_frame["max_minute"].max()),
                },
                "processed": {
                    "rows": len(processed_frame),
                    "feature_count": len(plan.feature_names),
                    "top_missing_rates": dict(
                        sorted(
                            missing_rates.items(),
                            key=lambda item: item[1],
                            reverse=True,
                        )[:10]
                    ),
                },
            },
            "publish_blocking_gate": False,
        },
        settings.validation_artifact_dir / "validation-summary.json",
    )
    return DataPreparationResult(command="validate", success=success)
