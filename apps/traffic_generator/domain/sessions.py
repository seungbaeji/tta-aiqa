"""Course collection session values handed from traffic generation to analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite
from pathlib import Path
from urllib.parse import urlsplit

OBSERVABILITY_SIGNALS = ("prometheus", "loki", "tempo")


def _validate_identifier(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty trimmed string")


def _parse_utc_timestamp(value: object, field_name: str) -> datetime:
    _validate_identifier(value, field_name)
    assert isinstance(value, str)
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO 8601 UTC timestamp") from error
    if not value.endswith("Z") or moment.tzinfo is None:
        raise ValueError(f"{field_name} must be an ISO 8601 UTC timestamp")
    if moment.utcoffset() != UTC.utcoffset(moment):
        raise ValueError(f"{field_name} must be an ISO 8601 UTC timestamp")
    return moment


def _validate_dashboard_url(value: object) -> None:
    if value is None:
        return
    _validate_identifier(value, "dashboard URL")
    assert isinstance(value, str)
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("dashboard URL must be an absolute HTTP(S) URL")


class SignalAvailabilityStatus(StrEnum):
    """Truthful collection-time arrival state for one telemetry backend."""

    NOT_CHECKED = "not_checked"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SignalAvailability:
    """One backend's explicitly observed availability and check time."""

    status: SignalAvailabilityStatus
    checked_at: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, SignalAvailabilityStatus):
            raise ValueError("signal availability status is invalid")
        if self.status is SignalAvailabilityStatus.NOT_CHECKED:
            if self.checked_at is not None:
                raise ValueError("unchecked signal must not have a check time")
        elif self.checked_at is None:
            raise ValueError("checked signal requires a check time")
        else:
            _parse_utc_timestamp(self.checked_at, "signal check time")

    def as_document(self) -> dict[str, object]:
        """Return one stable signal availability entry."""
        return {
            "status": self.status.value,
            "checked_at": self.checked_at,
        }


UNCHECKED_SIGNAL_AVAILABILITY = tuple(
    (
        signal,
        SignalAvailability(SignalAvailabilityStatus.NOT_CHECKED),
    )
    for signal in OBSERVABILITY_SIGNALS
)


@dataclass(frozen=True)
class CollectionModelIdentity:
    """Public model identity observed consistently during one collection session."""

    profile: str
    version: str
    threshold: float

    def __post_init__(self) -> None:
        _validate_identifier(self.profile, "model profile")
        _validate_identifier(self.version, "model version")
        if (
            isinstance(self.threshold, bool)
            or not isinstance(self.threshold, (int, float))
            or not isfinite(self.threshold)
            or not 0 < self.threshold < 1
        ):
            raise ValueError("model threshold must be between zero and one")

    def as_document(self) -> dict[str, object]:
        """Return the stable learner-facing model identity document."""
        return {
            "profile": self.profile,
            "version": self.version,
            "threshold": self.threshold,
        }


@dataclass(frozen=True)
class ScenarioCollection:
    """One scenario's bounded execution handoff within a course session."""

    name: str
    run_id: str
    started_at: str
    completed_at: str
    status_counts: tuple[tuple[int, int], ...]
    artifact_path: Path

    def __post_init__(self) -> None:
        _validate_identifier(self.name, "scenario name")
        _validate_identifier(self.run_id, "scenario run ID")
        started_at = _parse_utc_timestamp(self.started_at, "scenario start")
        completed_at = _parse_utc_timestamp(
            self.completed_at,
            "scenario completion",
        )
        if completed_at < started_at:
            raise ValueError("scenario completion must not precede start")
        if not self.status_counts:
            raise ValueError("scenario collection requires HTTP status counts")
        status_codes = [status for status, _ in self.status_counts]
        if (
            status_codes != sorted(status_codes)
            or len(status_codes) != len(set(status_codes))
            or any(
                not isinstance(status, int)
                or isinstance(status, bool)
                or not 100 <= status <= 599
                or not isinstance(count, int)
                or isinstance(count, bool)
                or count < 1
                for status, count in self.status_counts
            )
        ):
            raise ValueError(
                "scenario HTTP status counts must be sorted positive counts"
            )
        if not str(self.artifact_path):
            raise ValueError("scenario artifact path must not be empty")

    def as_document(self) -> dict[str, object]:
        """Return one stable scenario entry for the collection manifest."""
        return {
            "name": self.name,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status_counts": {
                str(status): count for status, count in self.status_counts
            },
            "artifact_path": str(self.artifact_path),
        }


@dataclass(frozen=True)
class CollectionSession:
    """Complete P5 collection handoff consumed during P6 analysis."""

    session_id: str
    started_at: str
    completed_at: str
    environment: str
    scope: str
    model_identity: CollectionModelIdentity
    manifest_path: Path
    scenarios: tuple[ScenarioCollection, ...]
    dashboard_url: str | None = None
    signal_availability: tuple[tuple[str, SignalAvailability], ...] = (
        UNCHECKED_SIGNAL_AVAILABILITY
    )

    def __post_init__(self) -> None:
        _validate_identifier(self.session_id, "collection session ID")
        started_at = _parse_utc_timestamp(
            self.started_at,
            "collection session start",
        )
        completed_at = _parse_utc_timestamp(
            self.completed_at,
            "collection session completion",
        )
        if completed_at < started_at:
            raise ValueError("collection session completion must not precede start")
        _validate_identifier(self.environment, "collection environment")
        if self.scope not in {"local", "target"}:
            raise ValueError("collection scope must be local or target")
        if not str(self.manifest_path):
            raise ValueError("collection manifest path must not be empty")
        _validate_dashboard_url(self.dashboard_url)
        names = [scenario.name for scenario in self.scenarios]
        run_ids = [scenario.run_id for scenario in self.scenarios]
        if names != ["baseline", "current-shift", "invalid"]:
            raise ValueError(
                "collection session requires baseline, current-shift, and invalid"
            )
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("collection scenario run IDs must be distinct")
        scenario_ranges = tuple(
            (
                _parse_utc_timestamp(scenario.started_at, "scenario start"),
                _parse_utc_timestamp(
                    scenario.completed_at,
                    "scenario completion",
                ),
            )
            for scenario in self.scenarios
        )
        if any(
            scenario_started < started_at or scenario_completed > completed_at
            for scenario_started, scenario_completed in scenario_ranges
        ):
            raise ValueError(
                "collection session range must contain every scenario range"
            )
        if any(
            previous[1] > following[0]
            for previous, following in zip(
                scenario_ranges,
                scenario_ranges[1:],
                strict=False,
            )
        ):
            raise ValueError(
                "collection scenario ranges must be ordered and non-overlapping"
            )
        signal_names = [name for name, _ in self.signal_availability]
        if signal_names != list(OBSERVABILITY_SIGNALS):
            raise ValueError("signal availability requires prometheus, loki, and tempo")
        if any(
            not isinstance(availability, SignalAvailability)
            for _, availability in self.signal_availability
        ):
            raise ValueError("signal availability entries are invalid")
        if any(
            availability.checked_at is not None
            and _parse_utc_timestamp(
                availability.checked_at,
                "signal check time",
            )
            < completed_at
            for _, availability in self.signal_availability
        ):
            raise ValueError("signal check time must not precede session completion")

    def as_document(self) -> dict[str, object]:
        """Return the versioned JSON-compatible P5-to-P6 handoff."""
        return {
            "schema_version": 1,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "environment": self.environment,
            "scope": self.scope,
            "dashboard_url": self.dashboard_url,
            "signal_availability": {
                name: availability.as_document()
                for name, availability in self.signal_availability
            },
            "model_identity": self.model_identity.as_document(),
            "manifest_path": str(self.manifest_path),
            "scenarios": [scenario.as_document() for scenario in self.scenarios],
        }
