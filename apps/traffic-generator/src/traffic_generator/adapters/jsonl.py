"""Traffic response and collection-session JSON evidence adapters."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from traffic_generator.domain import (
    OBSERVABILITY_SIGNALS,
    CollectionModelIdentity,
    CollectionSession,
    ScenarioCollection,
    SignalAvailability,
    SignalAvailabilityStatus,
    TrafficResponse,
)


class _ModelIdentityDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    profile: str
    version: str
    threshold: float


class _SignalAvailabilityDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    status: SignalAvailabilityStatus
    checked_at: str | None


class _ScenarioCollectionDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    run_id: str
    started_at: str
    completed_at: str
    status_counts: dict[str, int]
    artifact_path: Path


class _CollectionSessionDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1]
    session_id: str
    started_at: str
    completed_at: str
    environment: str
    scope: str
    dashboard_url: str | None
    signal_availability: dict[str, _SignalAvailabilityDocument]
    model_identity: _ModelIdentityDocument
    manifest_path: Path
    scenarios: list[_ScenarioCollectionDocument]


class JsonlTrafficRecorder:
    """Append traffic response evidence to one JSONL artifact path."""

    def __init__(self, path: Path) -> None:
        """Bind the append-only artifact location for this traffic process."""
        self._path = path

    def record(self, response: TrafficResponse) -> None:
        """Append one serialized response record without rewriting earlier evidence."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(asdict(response), sort_keys=True) + "\n")


class JsonCollectionSessionRecorder:
    """Atomically replace the latest complete P5-to-P6 session manifest."""

    def __init__(self, path: Path) -> None:
        """Bind the stable session manifest path."""
        self._path = path

    def write(self, session: CollectionSession) -> None:
        """Write one complete deterministic manifest without exposing a partial file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            temporary.write_text(
                json.dumps(
                    session.as_document(),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            temporary.replace(self._path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def read(self) -> CollectionSession:
        """Read and validate one complete session manifest."""
        document = _CollectionSessionDocument.model_validate_json(
            self._path.read_text(encoding="utf-8")
        )
        if set(document.signal_availability) != set(OBSERVABILITY_SIGNALS):
            raise ValueError("signal availability requires prometheus, loki, and tempo")
        return CollectionSession(
            session_id=document.session_id,
            started_at=document.started_at,
            completed_at=document.completed_at,
            environment=document.environment,
            scope=document.scope,
            dashboard_url=document.dashboard_url,
            signal_availability=tuple(
                (
                    signal,
                    SignalAvailability(
                        status=document.signal_availability[signal].status,
                        checked_at=document.signal_availability[signal].checked_at,
                    ),
                )
                for signal in OBSERVABILITY_SIGNALS
            ),
            model_identity=CollectionModelIdentity(
                profile=document.model_identity.profile,
                version=document.model_identity.version,
                threshold=document.model_identity.threshold,
            ),
            manifest_path=document.manifest_path,
            scenarios=tuple(
                ScenarioCollection(
                    name=scenario.name,
                    run_id=scenario.run_id,
                    started_at=scenario.started_at,
                    completed_at=scenario.completed_at,
                    status_counts=tuple(
                        sorted(
                            (int(status), count)
                            for status, count in scenario.status_counts.items()
                        )
                    ),
                    artifact_path=scenario.artifact_path,
                )
                for scenario in document.scenarios
            ),
        )
