"""Build raw-record quality profiles without a dataframe dependency."""

from dataclasses import dataclass

from aiqa_data.ports import PatientRecordRepository


@dataclass(frozen=True)
class RawRecordProfile:
    """Quality summary for one raw patient record without dataframe coupling."""

    record_id: int
    observation_count: int
    parameter_count: int
    sentinel_count: int
    min_minute: int
    max_minute: int


def profile_raw_records(
    records: PatientRecordRepository, missing_sentinel: float
) -> tuple[RawRecordProfile, ...]:
    """Profile raw record coverage and missing-sentinel use in deterministic order."""
    profiles: list[RawRecordProfile] = []
    for record in records.records():
        minutes = [item.minute for item in record.observations]
        parameters = {item.parameter for item in record.observations}
        profiles.append(
            RawRecordProfile(
                record_id=record.record_id,
                observation_count=len(record.observations),
                parameter_count=len(parameters),
                sentinel_count=sum(
                    item.value == missing_sentinel for item in record.observations
                ),
                min_minute=min(minutes, default=0),
                max_minute=max(minutes, default=0),
            )
        )
    return tuple(sorted(profiles, key=lambda item: item.record_id))
