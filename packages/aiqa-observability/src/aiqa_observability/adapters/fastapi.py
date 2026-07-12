"""FastAPI lifecycle and instrumentation bridges for the platform SDK."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from aiqa_observability.adapters.opentelemetry import TracingRuntime


def instrument_fastapi(app: FastAPI, tracing: TracingRuntime) -> None:
    """Attach FastAPI server spans to the package-owned tracer provider."""
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracing.provider)


def telemetry_lifespan(shutdown: Callable[[], None]):
    """Build a FastAPI lifespan that flushes telemetry after the app stops."""

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            shutdown()

    return lifespan
