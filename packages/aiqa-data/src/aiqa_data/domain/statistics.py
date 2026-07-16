"""Pure statistics used by patient-feature aggregation."""

from enum import StrEnum

from aiqa_data.domain.records import Observation


class Statistic(StrEnum):
    """Supported statistics for one time-ordered measurement series."""

    MIN = "min"
    MAX = "max"
    MEAN = "mean"
    LAST = "last"
    COUNT = "count"
    SUM = "sum"


def aggregate_observations(
    observations: tuple[Observation, ...],
    statistic: Statistic,
) -> float:
    """Calculate one configured statistic from timestamped observations."""
    if not observations:
        raise ValueError("statistic aggregation requires observations")
    ordered = tuple(sorted(observations, key=lambda item: (item.minute, item.value)))
    values = tuple(item.value for item in ordered)
    if statistic is Statistic.MIN:
        return min(values)
    if statistic is Statistic.MAX:
        return max(values)
    if statistic is Statistic.MEAN:
        return sum(values) / len(values)
    if statistic is Statistic.LAST:
        return ordered[-1].value
    if statistic is Statistic.COUNT:
        return float(len(values))
    if statistic is Statistic.SUM:
        return sum(values)
    raise ValueError(f"unsupported statistic: {statistic}")
