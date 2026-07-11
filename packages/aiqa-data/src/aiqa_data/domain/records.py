"""Patient record aggregation domain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Statistic(StrEnum):
    MIN = "min"
    MAX = "max"
    MEAN = "mean"
    LAST = "last"
    COUNT = "count"
    SUM = "sum"


@dataclass(frozen=True)
class Observation:
    minute: int
    parameter: str
    value: float

    def __post_init__(self) -> None:
        if self.minute < 0:
            raise ValueError("observation minute must not be negative")


@dataclass(frozen=True)
class PatientRecord:
    record_id: int
    observations: tuple[Observation, ...]


@dataclass(frozen=True)
class StaticFeatureRule:
    parameter: str
    output_name: str


@dataclass(frozen=True)
class SeriesFeatureRule:
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
    record_id: int
    target: int
    values: tuple[tuple[str, float | None], ...]

    def as_mapping(self) -> dict[str, float | int | None]:
        return {"record_id": self.record_id, **dict(self.values), "target": self.target}


def aggregate_record(
    record: PatientRecord, plan: AggregationPlan
) -> tuple[tuple[str, float | None], ...]:
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
        observations = sorted(
            grouped.get(rule.parameter, []), key=lambda item: (item.minute, item.value)
        )
        numbers = [observation.value for observation in observations]
        for statistic in rule.statistics:
            values.append(
                (
                    f"{rule.output_name}__{statistic.value}",
                    _aggregate(numbers, observations, statistic) if numbers else None,
                )
            )
        values.append((f"{rule.output_name}__missing", float(not observations)))
    return tuple(values)


def _aggregate(
    numbers: list[float], observations: list[Observation], statistic: Statistic
) -> float:
    if statistic is Statistic.MIN:
        return min(numbers)
    if statistic is Statistic.MAX:
        return max(numbers)
    if statistic is Statistic.MEAN:
        return sum(numbers) / len(numbers)
    if statistic is Statistic.LAST:
        return observations[-1].value
    if statistic is Statistic.COUNT:
        return float(len(numbers))
    if statistic is Statistic.SUM:
        return sum(numbers)
    raise ValueError(f"unsupported statistic: {statistic}")
