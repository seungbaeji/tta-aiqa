"""Prediction event domain object."""

from __future__ import annotations

from dataclasses import asdict, dataclass


# docs:start PredictionEvent
@dataclass(frozen=True)
class PredictionEvent:
    """Structured log event for one prediction request."""

    timestamp: str
    request_id: str
    trace_id: str
    model_version: str
    score: float
    threshold: float
    prediction: str
    latency_ms: float
    status_code: int
    validation_failure: bool
    client_id: str | None = None
    source_system: str | None = None
    failed_field: str | None = None
    error_category: str | None = None
    error_detail: str | None = None
    owner: str | None = None

    def to_dict(self) -> dict[str, str | float | int | bool | None]:
        """Return a JSON-serializable event."""
        return asdict(self)
# docs:end PredictionEvent
