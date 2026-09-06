"""Collect the three observability scenarios into one analysis handoff."""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from aiqa_observability import CORRELATION_ID_MAX_LENGTH, is_valid_correlation_id

from traffic_generator.domain import (
    OBSERVABILITY_SIGNALS,
    CollectionModelIdentity,
    CollectionSession,
    ScenarioCollection,
    SignalAvailability,
    SignalAvailabilityStatus,
    TrafficPlan,
    TrafficResponse,
)

COURSE_COLLECTION_SCENARIOS = ("baseline", "current-shift", "invalid")
SessionExecutor = Callable[[TrafficPlan, str], tuple[TrafficResponse, ...]]
Clock = Callable[[], datetime]


def utc_timestamp(moment: datetime) -> str:
    """Render one timezone-aware moment as a stable second-resolution UTC value."""
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("collection clock must return timezone-aware timestamps")
    return (
        moment.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def build_session_run_id(*, session_id: str, scenario: str) -> str:
    """Build one distinct bounded run ID for a scenario in a course session."""
    if not is_valid_correlation_id(session_id):
        raise ValueError("collection session ID must match the correlation ID contract")
    if not is_valid_correlation_id(scenario):
        raise ValueError("collection scenario must match the correlation ID contract")
    candidate = f"{session_id}-{scenario}"
    if is_valid_correlation_id(candidate):
        return candidate

    digest = hashlib.sha256(f"{session_id}\0{scenario}".encode()).hexdigest()[:24]
    suffix = f"-h{digest}"
    prefix_limit = CORRELATION_ID_MAX_LENGTH - len(suffix)
    prefix = session_id[:prefix_limit].rstrip("._-")
    run_id = f"{prefix}{suffix}"
    if not is_valid_correlation_id(run_id):
        raise AssertionError("generated session run ID violated its wire contract")
    return run_id


def response_model_identity(
    response: TrafficResponse,
) -> CollectionModelIdentity | None:
    """Extract the public model identity from one successful prediction response."""
    if not 200 <= response.status_code < 300:
        return None
    required = ("model_profile", "model_version", "threshold")
    if any(field not in response.body for field in required):
        raise ValueError("successful traffic response is missing model identity")
    profile = response.body["model_profile"]
    version = response.body["model_version"]
    threshold = response.body["threshold"]
    if (
        not isinstance(profile, str)
        or not isinstance(version, str)
        or isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
    ):
        raise ValueError("successful traffic response has invalid model identity")
    return CollectionModelIdentity(
        profile=profile,
        version=version,
        threshold=threshold,
    )


def update_signal_availability(
    session: CollectionSession,
    *,
    statuses: Mapping[str, str | SignalAvailabilityStatus],
    dashboard_url: str | None = None,
    now: Clock = lambda: datetime.now(UTC),
) -> CollectionSession:
    """Return a session with only explicitly checked signal states updated."""
    if not statuses and dashboard_url is None:
        raise ValueError("signal update requires a status or dashboard URL")
    unknown = sorted(set(statuses) - set(OBSERVABILITY_SIGNALS))
    if unknown:
        raise ValueError("unknown observability signals: " + ", ".join(unknown))

    checked_at = utc_timestamp(now()) if statuses else None
    availability = dict(session.signal_availability)
    for signal, raw_status in statuses.items():
        try:
            status = SignalAvailabilityStatus(raw_status)
        except ValueError as error:
            raise ValueError(
                f"signal status for {signal} must be available or unavailable"
            ) from error
        if status is SignalAvailabilityStatus.NOT_CHECKED:
            raise ValueError(
                f"signal status for {signal} must be available or unavailable"
            )
        assert checked_at is not None
        availability[signal] = SignalAvailability(
            status=status,
            checked_at=checked_at,
        )

    return replace(
        session,
        dashboard_url=(
            session.dashboard_url if dashboard_url is None else dashboard_url
        ),
        signal_availability=tuple(
            (signal, availability[signal]) for signal in OBSERVABILITY_SIGNALS
        ),
    )


def collect_course_session(
    plans: Mapping[str, TrafficPlan],
    *,
    execute: SessionExecutor,
    session_id: str,
    environment: str,
    scope: str,
    artifact_path: Path,
    manifest_path: Path,
    dashboard_url: str | None = None,
    now: Clock = lambda: datetime.now(UTC),
) -> CollectionSession:
    """Run the fixed course scenarios and return one validated analysis handoff."""
    if (
        not isinstance(environment, str)
        or not environment
        or environment != environment.strip()
    ):
        raise ValueError("collection environment must be a non-empty trimmed string")
    if scope not in {"local", "target"}:
        raise ValueError("collection scope must be local or target")
    missing = [
        scenario for scenario in COURSE_COLLECTION_SCENARIOS if scenario not in plans
    ]
    if missing:
        raise ValueError("course collection plans are missing: " + ", ".join(missing))

    session_started = utc_timestamp(now())
    collected: list[ScenarioCollection] = []
    observed_identity: CollectionModelIdentity | None = None
    for scenario in COURSE_COLLECTION_SCENARIOS:
        plan = plans[scenario]
        run_id = build_session_run_id(
            session_id=session_id,
            scenario=scenario,
        )
        scenario_started = utc_timestamp(now())
        responses = execute(plan, run_id)
        scenario_completed = utc_timestamp(now())
        if not responses:
            raise ValueError(
                f"course collection scenario returned no responses: {scenario}"
            )
        for response in responses:
            if response.run_id != run_id or response.scenario != scenario:
                raise ValueError(
                    "traffic response does not match its collection scenario"
                )
            identity = response_model_identity(response)
            if identity is None:
                continue
            if observed_identity is None:
                observed_identity = identity
            elif identity != observed_identity:
                raise ValueError("model identity changed during the collection session")
        collected.append(
            ScenarioCollection(
                name=scenario,
                run_id=run_id,
                started_at=scenario_started,
                completed_at=scenario_completed,
                status_counts=tuple(
                    sorted(Counter(item.status_code for item in responses).items())
                ),
                artifact_path=artifact_path,
            )
        )

    if observed_identity is None:
        raise ValueError("collection session did not observe a model identity")
    return CollectionSession(
        session_id=session_id,
        started_at=session_started,
        completed_at=utc_timestamp(now()),
        environment=environment,
        scope=scope,
        model_identity=observed_identity,
        manifest_path=manifest_path,
        scenarios=tuple(collected),
        dashboard_url=dashboard_url,
    )
