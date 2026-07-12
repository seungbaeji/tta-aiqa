"""Structured telemetry event domain values."""

from __future__ import annotations

from dataclasses import dataclass

from aiqa_observability.domain.attributes import (
    TelemetryAttributes,
    TelemetryValue,
    normalize_telemetry_attributes,
    validate_telemetry_attribute_pairs,
    validate_telemetry_event_name,
)


@dataclass(frozen=True)
class TelemetryEvent:
    """A named structured occurrence emitted by one application process."""

    name: str
    attributes: tuple[tuple[str, TelemetryValue], ...] = ()

    def __post_init__(self) -> None:
        validate_telemetry_event_name(self.name)
        validate_telemetry_attribute_pairs(self.attributes)

    @classmethod
    def create(
        cls, name: str, attributes: TelemetryAttributes | None = None
    ) -> TelemetryEvent:
        """Create an immutable event from a boundary attribute mapping."""
        return cls(name=name, attributes=normalize_telemetry_attributes(attributes))

    def as_fields(self) -> dict[str, TelemetryValue]:
        """Return event attributes for structured logs and trace events."""
        return dict(self.attributes)
