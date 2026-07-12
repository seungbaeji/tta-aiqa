"""Great Expectations adapter and suite contract tests."""

import subprocess
import sys

import pandas as pd
from data_quality_pipeline.adapters.expectations import (
    processed_expectations,
    raw_expectations,
)
from data_quality_pipeline.adapters.great_expectations import run_checkpoint
from data_quality_pipeline.adapters.quality import QualityRules


def test_data_quality_module_exposes_cli() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "data_quality_pipeline.main", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "validate" in result.stdout


def rules() -> QualityRules:
    return QualityRules.model_validate(
        {
            "schema_version": 1,
            "raw": {
                "expected_record_count": 2,
                "minimum_observation_count": 1,
                "maximum_minute": 2880,
            },
            "processed": {
                "expected_row_count": 2,
                "expected_positive_count": 1,
                "target_values": [0, 1],
                "missing_indicator_values": [0.0, 1.0],
            },
        }
    )


def test_raw_ingestion_suite_accepts_structurally_valid_profiles() -> None:
    frame = pd.DataFrame(
        [
            {
                "record_id": 1,
                "observation_count": 10,
                "parameter_count": 4,
                "sentinel_count": 1,
                "min_minute": 0,
                "max_minute": 120,
            },
            {
                "record_id": 2,
                "observation_count": 12,
                "parameter_count": 5,
                "sentinel_count": 0,
                "min_minute": 0,
                "max_minute": 180,
            },
        ]
    )

    result = run_checkpoint(
        frame, name="raw-unit", expectations=raw_expectations(rules())
    )

    assert result["success"] is True


def test_processed_suite_rejects_invalid_missing_indicator() -> None:
    frame = pd.DataFrame(
        {
            "record_id": [1, 2],
            "age": [50.0, 60.0],
            "age__missing": [0.0, 2.0],
            "target": [0, 1],
        }
    )

    result = run_checkpoint(
        frame,
        name="processed-unit",
        expectations=processed_expectations(rules(), ("age", "age__missing")),
    )

    assert result["success"] is False
