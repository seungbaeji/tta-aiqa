"""Traffic scenario outbound ports."""

from typing import Protocol

from traffic_generator.domain import TrafficResponse


class PatientPool(Protocol):
    @property
    def size(self) -> int: ...

    def patient(self, index: int) -> dict[str, object]: ...


class PredictionClient(Protocol):
    def predict(
        self,
        *,
        features: dict[str, object],
        request_id: str,
        scenario: str,
        timeout_seconds: float,
    ) -> TrafficResponse: ...


class TrafficRecorder(Protocol):
    def record(self, response: TrafficResponse) -> None: ...
