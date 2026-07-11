"""Request context domain object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4


# docs:start RequestContext
@dataclass(frozen=True)
class RequestContext:
    """Identifiers used to connect logs, metrics, and traces."""

    request_id: str
    trace_id: str
    timestamp: str

    @classmethod
    def create(
        cls,
        request_id: str | None = None,
        trace_id: str | None = None,
        timestamp: str | None = None,
    ) -> RequestContext:
        """Create a context with stable IDs for one request."""
        return cls(
            request_id=request_id or str(uuid4()),
            trace_id=trace_id or str(uuid4()),
            timestamp=timestamp or datetime.now(tz=UTC).isoformat(),
        )
# docs:end RequestContext
