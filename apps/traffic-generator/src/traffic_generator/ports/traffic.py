"""Traffic scenario outbound ports."""

from typing import Protocol

from traffic_generator.domain import TrafficResponse


class PatientPool(Protocol):
    """Select a target-free operational patient payload by deterministic index."""

    @property
    def size(self) -> int:
        """Return the number of available patient payloads."""
        ...

    def patient(self, index: int) -> dict[str, object]:
        """Return a defensive payload copy for the requested pool index."""
        ...


class PredictionClient(Protocol):
    """Send one generated payload to the public prediction API."""

    def predict(
        self,
        *,
        features: dict[str, object],
        request_id: str,
        scenario: str,
        timeout_seconds: float,
    ) -> TrafficResponse:
        """Return response evidence for one submitted traffic request."""
        ...


class TrafficRecorder(Protocol):
    """Persist one completed traffic response as append-only evidence."""

    def record(self, response: TrafficResponse) -> None:
        """Record the supplied traffic response evidence."""
        ...
