"""Execution-local telemetry context values and inheritance rules."""

from __future__ import annotations

from dataclasses import dataclass

from aiqa_observability.domain.attributes import (
    TelemetryAttributes,
    TelemetryValue,
    normalize_telemetry_attributes,
    validate_telemetry_attribute_pairs,
)


@dataclass(frozen=True)
class TelemetryContext:
    """Framework-neutral request, run, scenario, and operation correlation values."""

    operation: str
    request_id: str | None = None
    run_id: str | None = None
    scenario: str | None = None
    attributes: tuple[tuple[str, TelemetryValue], ...] = ()

    def __post_init__(self) -> None:
        validate_context_identifier(self.operation, "telemetry operation")
        if self.request_id is not None:
            validate_context_identifier(self.request_id, "request ID")
        if self.run_id is not None:
            validate_context_identifier(self.run_id, "run ID")
        if self.scenario is not None:
            validate_context_identifier(self.scenario, "scenario")
        validate_telemetry_attribute_pairs(self.attributes)

    @classmethod
    def create(
        cls,
        *,
        operation: str,
        request_id: str | None = None,
        run_id: str | None = None,
        scenario: str | None = None,
        attributes: TelemetryAttributes | None = None,
    ) -> TelemetryContext:
        """Create an immutable telemetry context from a boundary attribute mapping."""
        return cls(
            operation=operation,
            request_id=request_id,
            run_id=run_id,
            scenario=scenario,
            attributes=normalize_telemetry_attributes(attributes),
        )

    def as_log_fields(self) -> dict[str, TelemetryValue]:
        """Return context fields safe to attach to logs and trace spans."""
        fields: dict[str, TelemetryValue] = {"operation": self.operation}
        if self.request_id is not None:
            fields["request_id"] = self.request_id
        if self.run_id is not None:
            fields["run_id"] = self.run_id
        if self.scenario is not None:
            fields["scenario"] = self.scenario
        fields.update(self.attributes)
        return fields


def derive_telemetry_context(
    parent: TelemetryContext | None,
    *,
    operation: str,
    request_id: str | None = None,
    run_id: str | None = None,
    scenario: str | None = None,
    attributes: TelemetryAttributes | None = None,
) -> TelemetryContext:
    """Derive a child context while preserving inherited correlation values."""
    inherited = dict(parent.attributes) if parent is not None else {}
    if attributes is not None:
        inherited.update(attributes)
    return TelemetryContext.create(
        operation=operation,
        request_id=request_id
        if request_id is not None
        else (parent.request_id if parent is not None else None),
        run_id=run_id if run_id is not None else (parent.run_id if parent else None),
        scenario=scenario
        if scenario is not None
        else (parent.scenario if parent is not None else None),
        attributes=inherited,
    )


def validate_context_identifier(value: object, field_name: str) -> None:
    """Validate one non-empty, trimmed correlation or operation identifier."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty trimmed string")
