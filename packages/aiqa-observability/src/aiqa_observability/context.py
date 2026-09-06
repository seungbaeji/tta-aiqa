"""Execution-local context shared by logs and manual trace spans."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from aiqa_observability.domain import TelemetryContext

_CURRENT_CONTEXT: ContextVar[TelemetryContext | None] = ContextVar(
    "aiqa_telemetry_context", default=None
)


def current_context() -> TelemetryContext | None:
    """Return the context bound to the current execution path, if any."""
    return _CURRENT_CONTEXT.get()


@contextmanager
def bind_context(context: TelemetryContext) -> Iterator[TelemetryContext]:
    """Bind one context and reliably restore the previous execution context."""
    token = _CURRENT_CONTEXT.set(context)
    try:
        yield context
    finally:
        _CURRENT_CONTEXT.reset(token)
