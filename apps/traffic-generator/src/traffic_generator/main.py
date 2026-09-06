"""CLI entry point for deterministic traffic scenarios."""

import argparse
import json
import os
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Literal
from uuid import uuid4

from aiqa_observability import (
    CORRELATION_ID_MAX_LENGTH,
    CORRELATION_ID_PATTERN_TEXT,
)
from pydantic import BaseModel, ConfigDict, Field

from traffic_generator.adapters import JsonCollectionSessionRecorder
from traffic_generator.application import (
    build_session_run_id,
    collect_course_session,
    update_signal_availability,
)
from traffic_generator.bootstrap import TrafficRuntime, bootstrap
from traffic_generator.domain import TrafficPlan, TrafficResponse

TRAFFIC_GENERATE_OPERATION = "traffic.generate"
TRAFFIC_GENERATION_COMPLETED_EVENT = "traffic.generation.completed"
COURSE_SESSION_COMMAND = "course-session"
COURSE_SESSION_STATUS_COMMAND = "course-session-status"
SignalUpdateStatus = Literal["available", "unavailable"]


class TrafficCommandDto(BaseModel):
    """Validated command-line input for one traffic generation run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario: str = Field(min_length=1)
    request_count: int | None = Field(default=None, gt=0)
    run_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=CORRELATION_ID_MAX_LENGTH,
        pattern=CORRELATION_ID_PATTERN_TEXT,
    )
    session_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=CORRELATION_ID_MAX_LENGTH,
        pattern=CORRELATION_ID_PATTERN_TEXT,
    )
    fast: bool = False
    scope: Literal["local", "target"] | None = None
    manifest_path: Path | None = None
    dashboard_url: str | None = None
    prometheus: SignalUpdateStatus | None = None
    loki: SignalUpdateStatus | None = None
    tempo: SignalUpdateStatus | None = None


def run_plan(
    runtime: TrafficRuntime,
    plan: TrafficPlan,
    *,
    request_count: int | None,
    run_id: str | None,
) -> tuple[str, tuple[TrafficResponse, ...]]:
    """Execute one existing scenario under its telemetry run scope."""
    with runtime.telemetry.run_scope(
        TRAFFIC_GENERATE_OPERATION,
        run_id=run_id,
        scenario=plan.name,
    ) as context:
        assert context.run_id is not None
        responses = runtime.run(
            plan,
            request_count,
            run_id=context.run_id,
        )
        runtime.telemetry.event(
            TRAFFIC_GENERATION_COMPLETED_EVENT,
            attributes={
                "request_count": len(responses),
            },
        )
    return context.run_id, responses


def default_collection_manifest_path() -> Path:
    """Resolve the stable host or container default without bootstrapping traffic."""
    response_path = os.environ.get("AIQA_TRAFFIC_RESPONSE_ARTIFACT_PATH")
    if response_path:
        return Path(response_path).with_name("collection-session.json")
    return Path("artifacts/traffic/collection-session.json")


def print_session_manifest(session_document: dict[str, object]) -> None:
    """Print one machine-readable manifest document."""
    print(
        json.dumps(
            session_document,
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def ensure_session_id_has_no_traffic_evidence(
    response_path: Path,
    *,
    session_id: str,
    plans: dict[str, TrafficPlan],
) -> None:
    """Reject a session ID whose deterministic run IDs already appear in JSONL."""
    if not response_path.exists():
        return
    expected_run_ids = {
        build_session_run_id(session_id=session_id, scenario=scenario)
        for scenario in plans
    }
    with response_path.open(encoding="utf-8") as response_file:
        for line_number, line in enumerate(response_file, start=1):
            if not line.strip():
                continue
            try:
                document = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    "cannot verify session ID against invalid traffic evidence "
                    f"at {response_path}:{line_number}"
                ) from error
            if document.get("run_id") in expected_run_ids:
                raise ValueError(
                    f"session ID {session_id} already has traffic evidence"
                )


def validate_command_options(
    parser: argparse.ArgumentParser,
    command: TrafficCommandDto,
    signal_statuses: dict[str, SignalUpdateStatus],
) -> None:
    """Reject options that do not belong to the selected command."""
    if command.scenario == COURSE_SESSION_COMMAND:
        if (
            command.request_count is not None
            or command.fast
            or command.session_id is not None
        ):
            parser.error(
                "course-session does not accept --count, --fast, or --session-id"
            )
        if signal_statuses:
            parser.error(
                "--prometheus, --loki, and --tempo require course-session-status"
            )
        return
    if command.scenario == COURSE_SESSION_STATUS_COMMAND:
        if (
            command.request_count is not None
            or command.run_id
            or command.fast
            or command.scope is not None
        ):
            parser.error(
                "course-session-status does not accept "
                "--count, --run-id, --fast, or --scope"
            )
        if command.session_id is None:
            parser.error("course-session-status requires --session-id")
        if not signal_statuses and command.dashboard_url is None:
            parser.error(
                "course-session-status requires a signal result or --dashboard-url"
            )
        return
    if (
        command.scope is not None
        or command.session_id is not None
        or command.manifest_path is not None
        or command.dashboard_url is not None
        or signal_statuses
    ):
        parser.error(
            "individual scenarios do not accept --scope, --manifest-path, "
            "--session-id, --dashboard-url, or signal status options"
        )


def main() -> None:
    """Parse CLI input, invoke the bound operation, and render its summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario",
        help=("configured scenario name, course-session, or course-session-status"),
    )
    parser.add_argument("--count", dest="request_count", type=int)
    parser.add_argument("--run-id")
    parser.add_argument(
        "--session-id",
        help="expected complete session ID for course-session-status",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="single scenario only: skip pacing and post-run collection wait",
    )
    parser.add_argument(
        "--scope",
        choices=("local", "target"),
        help="evidence scope recorded by the course-session command",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        help=("course-session create/update file; defaults beside response JSONL"),
    )
    parser.add_argument(
        "--dashboard-url",
        help="Grafana dashboard URL stored in the collection manifest",
    )
    for signal in ("prometheus", "loki", "tempo"):
        parser.add_argument(
            f"--{signal}",
            choices=("available", "unavailable"),
            help=(f"explicit {signal} arrival result for course-session-status"),
        )
    command = TrafficCommandDto.model_validate(vars(parser.parse_args()))
    signal_statuses = {
        signal: status
        for signal in ("prometheus", "loki", "tempo")
        if (status := getattr(command, signal)) is not None
    }
    validate_command_options(parser, command, signal_statuses)
    if command.scenario == COURSE_SESSION_STATUS_COMMAND:
        manifest_path = command.manifest_path or default_collection_manifest_path()
        recorder = JsonCollectionSessionRecorder(manifest_path)
        current_session = recorder.read()
        if current_session.session_id != command.session_id:
            raise ValueError(
                f"requested session {command.session_id} does not match "
                f"manifest session {current_session.session_id}"
            )
        session = update_signal_availability(
            current_session,
            statuses=signal_statuses,
            dashboard_url=command.dashboard_url,
        )
        recorder.write(session)
        print_session_manifest(session.as_document())
        return
    runtime = bootstrap()
    try:
        if command.scenario == COURSE_SESSION_COMMAND:
            plans = runtime.plans
            session_id = command.run_id or str(uuid4())
            recorder_path = command.manifest_path or (
                runtime.response_artifact_path.with_name("collection-session.json")
            )
            recorder = JsonCollectionSessionRecorder(recorder_path)
            if recorder_path.exists() and recorder.read().session_id == session_id:
                raise ValueError(
                    f"session ID {session_id} is already the latest complete session"
                )
            ensure_session_id_has_no_traffic_evidence(
                runtime.response_artifact_path,
                session_id=session_id,
                plans=plans,
            )
            portable_manifest_path = (
                command.manifest_path or runtime.portable_manifest_path
            )

            def execute(
                plan: TrafficPlan,
                run_id: str,
            ) -> tuple[TrafficResponse, ...]:
                return run_plan(
                    runtime,
                    plan,
                    request_count=None,
                    run_id=run_id,
                )[1]

            session = collect_course_session(
                plans,
                execute=execute,
                session_id=session_id,
                environment=runtime.environment,
                scope=command.scope or "local",
                artifact_path=runtime.portable_response_artifact_path,
                manifest_path=portable_manifest_path,
                dashboard_url=command.dashboard_url,
            )
            recorder.write(session)
            print_session_manifest(session.as_document())
            return

        plan = runtime.plans.get(command.scenario)
        if plan is None:
            raise ValueError(f"unknown traffic scenario: {command.scenario}")
        if command.fast:
            plan = replace(
                plan,
                interval_seconds=0,
                collection_wait_seconds=0,
            )
        run_id, responses = run_plan(
            runtime,
            plan,
            request_count=command.request_count,
            run_id=command.run_id,
        )
    finally:
        runtime.telemetry.shutdown()
    print(
        {
            "run_id": run_id,
            "status_codes": dict(
                Counter(response.status_code for response in responses)
            ),
        }
    )
