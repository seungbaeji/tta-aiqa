"""Patient-level aggregation domain tests."""

from aiqa_data.domain import (
    AggregationPlan,
    Observation,
    PatientRecord,
    SeriesFeatureRule,
    StaticFeatureRule,
    Statistic,
    aggregate_record,
)


def test_aggregation_normalizes_sentinel_and_uses_time_order() -> None:
    plan = AggregationPlan(
        missing_sentinel=-1.0,
        static_features=(StaticFeatureRule("Age", "age"),),
        series_features=(
            SeriesFeatureRule(
                "Urine",
                "urine",
                (Statistic.MIN, Statistic.LAST, Statistic.COUNT, Statistic.SUM),
            ),
        ),
    )
    record = PatientRecord(
        record_id=1,
        observations=(
            Observation(0, "Age", 67.0),
            Observation(120, "Urine", 20.0),
            Observation(120, "Urine", 15.0),
            Observation(60, "Urine", 10.0),
            Observation(180, "Urine", -1.0),
        ),
    )

    values = dict(aggregate_record(record, plan))

    assert values == {
        "age": 67.0,
        "age__missing": 0.0,
        "urine__min": 10.0,
        "urine__last": 20.0,
        "urine__count": 3.0,
        "urine__sum": 45.0,
        "urine__missing": 0.0,
    }


def test_missing_series_produces_null_statistics_and_indicator() -> None:
    plan = AggregationPlan(
        missing_sentinel=-1.0,
        static_features=(),
        series_features=(SeriesFeatureRule("Lactate", "lactate", (Statistic.MEAN,)),),
    )

    values = dict(aggregate_record(PatientRecord(1, ()), plan))

    assert values == {"lactate__mean": None, "lactate__missing": 1.0}
