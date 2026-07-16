"""Expectation suites derived from versioned quality and feature contracts."""

from great_expectations import expectations as gxe
from great_expectations.expectations.expectation import Expectation

from data_quality_pipeline.adapters.quality import QualityRules

RAW_PROFILE_COLUMNS = [
    "record_id",
    "observation_count",
    "parameter_count",
    "sentinel_count",
    "min_minute",
    "max_minute",
]


def raw_expectations(rules: QualityRules) -> list[Expectation]:
    """Build raw-record ingestion expectations from the versioned quality policy."""
    return [
        gxe.ExpectTableColumnsToMatchOrderedList(column_list=RAW_PROFILE_COLUMNS),
        gxe.ExpectTableRowCountToEqual(value=rules.raw.expected_record_count),
        gxe.ExpectColumnValuesToNotBeNull(column="record_id"),
        gxe.ExpectColumnValuesToBeUnique(column="record_id"),
        gxe.ExpectColumnValuesToBeBetween(
            column="observation_count",
            min_value=rules.raw.minimum_observation_count,
        ),
        gxe.ExpectColumnValuesToBeBetween(column="sentinel_count", min_value=0),
        gxe.ExpectColumnValuesToBeBetween(column="min_minute", min_value=0),
        gxe.ExpectColumnValuesToBeBetween(
            column="max_minute", min_value=0, max_value=rules.raw.maximum_minute
        ),
    ]


def processed_expectations(
    rules: QualityRules, feature_names: tuple[str, ...]
) -> list[Expectation]:
    """Build processed-feature expectations from quality and aggregation contracts."""
    expectations: list[Expectation] = [
        gxe.ExpectTableColumnsToMatchOrderedList(
            column_list=["record_id", *feature_names, "target"]
        ),
        gxe.ExpectTableRowCountToEqual(value=rules.processed.expected_row_count),
        gxe.ExpectColumnValuesToNotBeNull(column="record_id"),
        gxe.ExpectColumnValuesToBeUnique(column="record_id"),
        gxe.ExpectColumnValuesToNotBeNull(column="target"),
        gxe.ExpectColumnValuesToBeInSet(
            column="target", value_set=list(rules.processed.target_values)
        ),
        gxe.ExpectColumnSumToBeBetween(
            column="target",
            min_value=rules.processed.expected_positive_count,
            max_value=rules.processed.expected_positive_count,
        ),
    ]
    for feature in feature_names:
        if feature.endswith("__missing"):
            expectations.extend(
                [
                    gxe.ExpectColumnValuesToNotBeNull(column=feature),
                    gxe.ExpectColumnValuesToBeInSet(
                        column=feature,
                        value_set=list(rules.processed.missing_indicator_values),
                    ),
                ]
            )
    return expectations
