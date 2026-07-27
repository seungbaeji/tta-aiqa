"""Traffic CLI compatibility and course-session delivery tests."""

from __future__ import annotations

import json
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from traffic_generator import main as traffic_main
from traffic_generator.adapters import JsonCollectionSessionRecorder
from traffic_generator.domain import (
    InvalidTrafficCase,
    ScenarioMode,
    TrafficPlan,
    TrafficResponse,
)


@dataclass(frozen=True)
class BoundContext:
    """Minimal telemetry context yielded to the CLI."""

    run_id: str


@dataclass
class StubTelemetry:
    """Observe CLI lifecycle without requiring a telemetry backend."""

    shutdown_called: bool = False

    @contextmanager
    def run_scope(
        self,
        _operation: str,
        *,
        run_id: str | None,
        scenario: str,
    ):
        assert scenario
        yield BoundContext(run_id or "generated-run")

    def event(self, _name: str, *, attributes: dict[str, int]) -> None:
        assert attributes["request_count"] > 0

    def shutdown(self) -> None:
        self.shutdown_called = True


@dataclass
class StubRuntime:
    """Run configured scenarios and expose the fields used by the CLI."""

    response_artifact_path: Path
    portable_response_artifact_path: Path = Path("artifacts/traffic/compose.jsonl")
    portable_manifest_path: Path = Path("artifacts/traffic/collection-session.json")
    environment: str = "compose"
    telemetry: StubTelemetry = field(default_factory=StubTelemetry)
    calls: list[tuple[str, int | None, str]] = field(default_factory=list)

    @property
    def plans(self) -> dict[str, TrafficPlan]:
        return {
            name: TrafficPlan(
                name=name,
                mode=(
                    ScenarioMode.INVALID if name == "invalid" else ScenarioMode.VALID
                ),
                request_count=1,
                interval_seconds=0,
                timeout_seconds=1,
                invalid_cases=(
                    (InvalidTrafficCase.MISSING_FEATURE,) if name == "invalid" else ()
                ),
            )
            for name in ("baseline", "current-shift", "invalid")
        }

    def run(
        self,
        plan: TrafficPlan,
        count: int | None,
        run_id: str,
    ) -> tuple[TrafficResponse, ...]:
        self.calls.append((plan.name, count, run_id))
        status_code = 422 if plan.name == "invalid" else 200
        body: dict[str, object] = (
            {"detail": {"code": "MODEL_INPUT_INVALID"}}
            if status_code == 422
            else {
                "model_profile": "baseline",
                "model_version": "baseline-f2576f12512a",
                "threshold": 0.5,
            }
        )
        return (
            TrafficResponse(
                request_id=f"{plan.name}-{run_id}-0001",
                run_id=run_id,
                scenario=plan.name,
                status_code=status_code,
                elapsed_seconds=0.01,
                body=body,
            ),
        )


def test_existing_single_scenario_command_keeps_its_summary(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    runtime = StubRuntime(tmp_path / "compose.jsonl")
    monkeypatch.setattr(traffic_main, "bootstrap", lambda: runtime)
    monkeypatch.setattr(
        "sys.argv",
        [
            "aiqa-traffic",
            "baseline",
            "--count",
            "1",
            "--run-id",
            "legacy-run",
            "--fast",
        ],
    )

    traffic_main.main()

    assert runtime.calls == [("baseline", 1, "legacy-run")]
    assert capsys.readouterr().out.strip() == (
        "{'run_id': 'legacy-run', 'status_codes': {200: 1}}"
    )
    assert runtime.telemetry.shutdown_called is True


def test_course_session_command_writes_and_outputs_the_same_manifest(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    runtime = StubRuntime(tmp_path / "compose.jsonl")
    manifest_path = tmp_path / "collection-session.json"
    monkeypatch.setattr(traffic_main, "bootstrap", lambda: runtime)
    monkeypatch.setattr(
        "sys.argv",
        [
            "aiqa-traffic",
            "course-session",
            "--run-id",
            "class-session-01",
            "--scope",
            "local",
        ],
    )

    traffic_main.main()

    output = json.loads(capsys.readouterr().out)
    stored = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert output == stored
    assert output["session_id"] == "class-session-01"
    assert output["environment"] == "compose"
    assert output["scope"] == "local"
    assert output["manifest_path"] == ("artifacts/traffic/collection-session.json")
    assert [item["name"] for item in output["scenarios"]] == [
        "baseline",
        "current-shift",
        "invalid",
    ]
    assert [item["status_counts"] for item in output["scenarios"]] == [
        {"200": 1},
        {"200": 1},
        {"422": 1},
    ]
    assert {item["artifact_path"] for item in output["scenarios"]} == {
        "artifacts/traffic/compose.jsonl"
    }
    assert output["dashboard_url"] is None
    assert output["signal_availability"] == {
        name: {"status": "not_checked", "checked_at": None}
        for name in ("prometheus", "loki", "tempo")
    }
    assert runtime.telemetry.shutdown_called is True


def test_course_session_status_updates_manifest_without_bootstrapping_traffic(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    runtime = StubRuntime(tmp_path / "compose.jsonl")
    manifest_path = tmp_path / "collection-session.json"
    monkeypatch.setattr(traffic_main, "bootstrap", lambda: runtime)
    monkeypatch.setattr(
        "sys.argv",
        [
            "aiqa-traffic",
            "course-session",
            "--run-id",
            "class-session-01",
        ],
    )
    traffic_main.main()
    capsys.readouterr()
    monkeypatch.setattr(
        traffic_main,
        "bootstrap",
        lambda: (_ for _ in ()).throw(
            AssertionError("status update must not bootstrap traffic")
        ),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "aiqa-traffic",
            "course-session-status",
            "--session-id",
            "class-session-01",
            "--manifest-path",
            str(manifest_path),
            "--dashboard-url",
            "https://example.grafana.net/d/tta-aiqa-quality/service-quality",
            "--prometheus",
            "available",
            "--loki",
            "unavailable",
        ],
    )

    traffic_main.main()

    output = json.loads(capsys.readouterr().out)
    stored = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert output == stored
    assert JsonCollectionSessionRecorder(manifest_path).read().as_document() == stored
    assert output["session_id"] == "class-session-01"
    assert output["dashboard_url"] == (
        "https://example.grafana.net/d/tta-aiqa-quality/service-quality"
    )
    assert output["signal_availability"]["prometheus"]["status"] == "available"
    assert output["signal_availability"]["loki"]["status"] == "unavailable"
    assert output["signal_availability"]["tempo"] == {
        "status": "not_checked",
        "checked_at": None,
    }
    assert re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
        output["signal_availability"]["prometheus"]["checked_at"],
    )


@pytest.mark.parametrize(
    "arguments",
    [
        ["course-session", "--fast"],
        ["course-session", "--count", "1"],
        ["course-session", "--prometheus", "available"],
        ["course-session", "--session-id", "irrelevant"],
        ["baseline", "--scope", "target"],
        ["baseline", "--session-id", "irrelevant"],
        ["baseline", "--manifest-path", "ignored.json"],
        [
            "baseline",
            "--dashboard-url",
            "https://example.grafana.net/d/tta-aiqa-quality",
        ],
        ["baseline", "--prometheus", "available"],
        [
            "course-session-status",
            "--session-id",
            "class-session-01",
            "--scope",
            "target",
            "--prometheus",
            "available",
        ],
        [
            "course-session-status",
            "--session-id",
            "class-session-01",
            "--run-id",
            "irrelevant",
            "--prometheus",
            "available",
        ],
        ["course-session-status", "--prometheus", "available"],
    ],
)
def test_commands_reject_irrelevant_options_before_bootstrap(
    arguments: list[str],
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        traffic_main,
        "bootstrap",
        lambda: (_ for _ in ()).throw(
            AssertionError("invalid command must not bootstrap traffic")
        ),
    )
    monkeypatch.setattr("sys.argv", ["aiqa-traffic", *arguments])

    with pytest.raises(SystemExit):
        traffic_main.main()


def test_course_session_status_rejects_a_stale_manifest(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime = StubRuntime(tmp_path / "compose.jsonl")
    manifest_path = tmp_path / "collection-session.json"
    monkeypatch.setattr(traffic_main, "bootstrap", lambda: runtime)
    monkeypatch.setattr(
        "sys.argv",
        [
            "aiqa-traffic",
            "course-session",
            "--run-id",
            "class-session-01",
        ],
    )
    traffic_main.main()
    before = manifest_path.read_text(encoding="utf-8")
    monkeypatch.setattr(
        traffic_main,
        "bootstrap",
        lambda: (_ for _ in ()).throw(
            AssertionError("status update must not bootstrap traffic")
        ),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "aiqa-traffic",
            "course-session-status",
            "--session-id",
            "class-session-02",
            "--manifest-path",
            str(manifest_path),
            "--prometheus",
            "available",
        ],
    )

    with pytest.raises(
        ValueError,
        match="requested session class-session-02 does not match manifest session",
    ):
        traffic_main.main()

    assert manifest_path.read_text(encoding="utf-8") == before


def test_course_session_rejects_reusing_the_latest_session_id(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime = StubRuntime(tmp_path / "compose.jsonl")
    monkeypatch.setattr(traffic_main, "bootstrap", lambda: runtime)
    monkeypatch.setattr(
        "sys.argv",
        [
            "aiqa-traffic",
            "course-session",
            "--run-id",
            "class-session-01",
        ],
    )
    traffic_main.main()
    runtime.calls.clear()
    runtime.telemetry.shutdown_called = False

    with pytest.raises(
        ValueError,
        match="session ID class-session-01 is already the latest complete session",
    ):
        traffic_main.main()

    assert runtime.calls == []
    assert runtime.telemetry.shutdown_called is True


def test_course_session_rejects_an_id_found_in_partial_traffic_evidence(
    monkeypatch,
    tmp_path: Path,
) -> None:
    response_path = tmp_path / "compose.jsonl"
    response_path.write_text(
        '{"run_id":"class-session-02-baseline","status_code":200}\n',
        encoding="utf-8",
    )
    runtime = StubRuntime(response_path)
    monkeypatch.setattr(traffic_main, "bootstrap", lambda: runtime)
    monkeypatch.setattr(
        "sys.argv",
        [
            "aiqa-traffic",
            "course-session",
            "--run-id",
            "class-session-02",
        ],
    )

    with pytest.raises(
        ValueError,
        match="session ID class-session-02 already has traffic evidence",
    ):
        traffic_main.main()

    assert runtime.calls == []
    assert runtime.telemetry.shutdown_called is True
    assert not (tmp_path / "collection-session.json").exists()


def test_course_session_shuts_down_telemetry_when_execution_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime = StubRuntime(tmp_path / "compose.jsonl")

    def fail_run(
        _plan: TrafficPlan,
        _count: int | None,
        _run_id: str,
    ) -> tuple[TrafficResponse, ...]:
        raise RuntimeError("prediction unavailable")

    monkeypatch.setattr(runtime, "run", fail_run)
    monkeypatch.setattr(traffic_main, "bootstrap", lambda: runtime)
    monkeypatch.setattr(
        "sys.argv",
        [
            "aiqa-traffic",
            "course-session",
            "--run-id",
            "class-session-01",
        ],
    )

    with pytest.raises(RuntimeError, match="prediction unavailable"):
        traffic_main.main()

    assert runtime.telemetry.shutdown_called is True
    assert not (tmp_path / "collection-session.json").exists()
