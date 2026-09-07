"""Expectation suites derived from versioned quality and feature contracts."""

from great_expectations import expectations as gxe
from great_expectations.expectations.expectation import Expectation

from data_quality_pipeline.adapters.quality import QualityRules

# 원본 파일을 그대로 넣지 않습니다. 기록별 요약 표의 열 순서입니다.
RAW_PROFILE_COLUMNS = [
    "record_id",
    "observation_count",
    "parameter_count",
    "sentinel_count",
    "min_minute",
    "max_minute",
]


def raw_expectations(rules: QualityRules) -> list[Expectation]:
    """Build raw-record ingestion expectations from the versioned quality policy.

    숫자는 configs/data/quality-rules.yaml 의 raw 칸입니다.
    결측 표식 `-1`이 있다는 사실이 아니라, 식별자와 48시간(2,880분) 창을 검사합니다.
    """
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
        # maximum_minute=2880 은 입실 후 48시간 관측 창입니다.
        gxe.ExpectColumnValuesToBeBetween(
            column="max_minute", min_value=0, max_value=rules.raw.maximum_minute
        ),
    ]


def processed_expectations(
    rules: QualityRules, feature_names: tuple[str, ...]
) -> list[Expectation]:
    """Build processed-feature expectations from quality and aggregation contracts.

    가공 표는 record_id + 133개 특성 + target 이어야 합니다.
    high_risk 건수는 expected_positive_count(554)와 같아야 합니다.
    """
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
    # __missing 열은 0/1만 허용합니다. 결측 여부 표식이지 측정값이 아닙니다.
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
