"""Great Expectations quality-validation adapter for Data Quality Pipeline."""

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
from aiqa_data.application import profile_raw_records
from aiqa_data.domain import AggregationPlan
from aiqa_data.ports import PatientRecordRepository

from data_quality_pipeline.adapters.evidence import (
    ProcessedValidationProfileDocument,
    RawValidationProfileDocument,
    ValidationProfileDocument,
    ValidationSummaryDocument,
    write_validation_summary,
)
from data_quality_pipeline.adapters.expectations import (
    processed_expectations,
    raw_expectations,
)
from data_quality_pipeline.adapters.great_expectations import run_checkpoint
from data_quality_pipeline.adapters.quality import QualityRules


@dataclass(frozen=True)
class GreatExpectationsQualityValidator:
    """Run raw and processed checkpoints for one configured data-quality policy."""

    records: PatientRecordRepository
    aggregation_plan: AggregationPlan
    rules: QualityRules

    def validate(self, patient_features_path: Path, artifact_dir: Path) -> bool:
        """Write GE evidence and return whether raw and processed checks both passed."""
        raw_frame = pd.DataFrame(
            asdict(item)
            for item in profile_raw_records(
                self.records,
                self.aggregation_plan.missing_sentinel,
            )
        )
        processed_frame = pd.read_csv(patient_features_path)
        raw_result = run_checkpoint(
            raw_frame,
            name="raw-ingestion",
            expectations=raw_expectations(self.rules),
            project_root=artifact_dir / "raw",
        )
        processed_result = run_checkpoint(
            processed_frame,
            name="processed-readiness",
            expectations=processed_expectations(
                self.rules,
                self.aggregation_plan.feature_names,
            ),
            project_root=artifact_dir / "processed",
        )
        success = bool(raw_result["success"] and processed_result["success"])
        document = ValidationSummaryDocument(
            schema_version=1,
            success=success,
            raw_ingestion=raw_result,
            processed_readiness=processed_result,
            profile=ValidationProfileDocument(
                raw=RawValidationProfileDocument(
                    records=len(raw_frame),
                    observations=int(raw_frame["observation_count"].sum()),
                    sentinels=int(raw_frame["sentinel_count"].sum()),
                    maximum_minute=int(raw_frame["max_minute"].max()),
                ),
                processed=ProcessedValidationProfileDocument(
                    rows=len(processed_frame),
                    feature_count=len(self.aggregation_plan.feature_names),
                    top_missing_rates=top_missing_rates(processed_frame),
                ),
            ),
            publish_blocking_gate=False,
        )
        write_validation_summary(document, artifact_dir / "validation-summary.json")
        return success


def top_missing_rates(processed_frame: pd.DataFrame) -> dict[str, float]:
    """Return the ten highest missing-indicator rates in deterministic order."""
    missing_columns = [
        column for column in processed_frame.columns if column.endswith("__missing")
    ]
    rates = {
        column.removesuffix("__missing"): float(processed_frame[column].mean())
        for column in missing_columns
    }
    return dict(
        sorted(rates.items(), key=lambda item: item[1], reverse=True)[:10]
    )
