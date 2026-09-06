"""OpenTelemetry tracing runtime and OTLP endpoint adapters."""

from aiqa_observability.adapters.opentelemetry.endpoint import (
    normalize_traces_endpoint,
)
from aiqa_observability.adapters.opentelemetry.runtime import TracingRuntime

__all__ = ["TracingRuntime", "normalize_traces_endpoint"]
