"""Patient-level feature aggregation domain values and behavior."""

from dataclasses import dataclass

from aiqa_data.domain.records import Observation, PatientRecord
from aiqa_data.domain.statistics import Statistic, aggregate_observations


@dataclass(frozen=True)
class StaticFeatureRule:
    """Map one static source parameter to a canonical feature name."""

    parameter: str
    output_name: str


@dataclass(frozen=True)
class SeriesFeatureRule:
    """Map one measurement series to one or more configured statistics."""

    parameter: str
    output_name: str
    statistics: tuple[Statistic, ...]

    def __post_init__(self) -> None:
        if not self.statistics:
            raise ValueError("series feature must define statistics")
        if len(self.statistics) != len(set(self.statistics)):
            raise ValueError("series statistics must be unique")


@dataclass(frozen=True)
class AggregationPlan:
    """Immutable rules for converting one raw patient record into features."""

    missing_sentinel: float
    static_features: tuple[StaticFeatureRule, ...]
    series_features: tuple[SeriesFeatureRule, ...]

    def __post_init__(self) -> None:
        output_names = [rule.output_name for rule in self.static_features]
        output_names.extend(rule.output_name for rule in self.series_features)
        if len(output_names) != len(set(output_names)):
            raise ValueError("aggregation output names must be unique")

    @property
    def feature_names(self) -> tuple[str, ...]:
        """Return the canonical patient-level feature order produced by this plan."""
        names: list[str] = []
        for rule in self.static_features:
            names.extend((rule.output_name, f"{rule.output_name}__missing"))
        for rule in self.series_features:
            names.extend(
                f"{rule.output_name}__{statistic.value}"
                for statistic in rule.statistics
            )
            names.append(f"{rule.output_name}__missing")
        return tuple(names)


@dataclass(frozen=True)
class PatientFeatureRow:
    """One patient-level feature row with its supervised training target."""

    record_id: int
    target: int
    values: tuple[tuple[str, float | None], ...]

    def as_mapping(self) -> dict[str, float | int | None]:
        """Return a value mapping for an adapter that serializes this row."""
        return {"record_id": self.record_id, **dict(self.values), "target": self.target}


def aggregate_record(
    record: PatientRecord,
    plan: AggregationPlan,
) -> tuple[tuple[str, float | None], ...]:
    """Transform one raw patient record into ordered, missing-aware feature values."""
    grouped: dict[str, list[Observation]] = {}
    for observation in record.observations:
        if observation.value == plan.missing_sentinel:
            continue
        grouped.setdefault(observation.parameter, []).append(observation)

    values: list[tuple[str, float | None]] = []
    for rule in plan.static_features:
        observations = grouped.get(rule.parameter, [])
        value = observations[0].value if observations else None
        values.append((rule.output_name, value))
        values.append((f"{rule.output_name}__missing", float(not observations)))

    for rule in plan.series_features:
        observations = tuple(grouped.get(rule.parameter, ()))
        for statistic in rule.statistics:
            values.append(
                (
                    f"{rule.output_name}__{statistic.value}",
                    aggregate_observations(observations, statistic)
                    if observations
                    else None,
                )
            )
        values.append((f"{rule.output_name}__missing", float(not observations)))
    return tuple(values)
