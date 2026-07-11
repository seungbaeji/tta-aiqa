"""Risk API adapters connecting serving events to operational telemetry."""

from dataclasses import asdict

from aiqa_observability.adapters import TelemetryRuntime
from aiqa_observability.domain import PredictionObservation
from aiqa_serving.domain import PredictionEvent
from opentelemetry import trace


class PredictionTelemetryRecorder:
    def __init__(self, runtime: TelemetryRuntime) -> None:
        self._runtime = runtime

    def record(self, event: PredictionEvent) -> None:
        self._runtime.record_prediction(
            PredictionObservation(**asdict(event), trace_id=current_trace_id())
        )


def current_trace_id() -> str:
    context = trace.get_current_span().get_span_context()
    return f"{context.trace_id:032x}" if context.is_valid else ""
