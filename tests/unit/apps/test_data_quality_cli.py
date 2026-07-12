"""Data Quality Pipeline CLI outcome tests."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from data_quality_pipeline import main as cli
from data_quality_pipeline.bootstrap import DataPreparationResult


class TelemetrySpy:
    """Minimal telemetry facade used to assert CLI outcome signaling."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []
        self.shutdown_called = False

    @contextmanager
    def run_scope(self, *_: object, **__: object) -> Iterator[None]:
        """Re-raise command failures as the real telemetry scope does."""
        yield

    def event(
        self,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
        **_: object,
    ) -> None:
        """Capture the event name and attributes supplied by the CLI."""
        self.events.append((name, attributes or {}))

    def shutdown(self) -> None:
        """Record lifecycle cleanup."""
        self.shutdown_called = True


def test_validation_failure_emits_failed_event_and_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry = TelemetrySpy()
    args = SimpleNamespace(
        command="validate",
        source_contract="source.yaml",
        aggregation_config="aggregation.yaml",
        split_config="split.yaml",
        patient_features="features.csv",
        split_manifest="manifest.csv",
        split_dataset_dir="datasets",
        source_evidence="source.json",
        quality_rules="quality.yaml",
        validation_artifact_dir="validation",
    )
    settings = SimpleNamespace(
        environment="test",
        telemetry_config_path=Path("configs/observability/telemetry.yaml"),
        otlp_endpoint=None,
    )

    monkeypatch.setattr(cli, "parse_args", lambda: args)
    monkeypatch.setattr(cli, "DataQualitySettings", lambda **_: settings)
    monkeypatch.setattr(cli, "create_telemetry", lambda **_: telemetry)
    monkeypatch.setitem(
        cli.COMMANDS,
        "validate",
        lambda _: DataPreparationResult(command="validate", success=False),
    )

    with pytest.raises(SystemExit, match="1"):
        cli.main()

    assert telemetry.shutdown_called is True
    assert [name for name, _ in telemetry.events] == ["data_quality.command.failed"]
    assert telemetry.events[0][1]["success"] is False
