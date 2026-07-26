"""CLI entry point for deterministic traffic scenarios."""

import argparse
from collections import Counter
from dataclasses import replace

from aiqa_observability import (
    CORRELATION_ID_MAX_LENGTH,
    CORRELATION_ID_PATTERN_TEXT,
)
from pydantic import BaseModel, ConfigDict, Field

from traffic_generator.bootstrap import bootstrap

TRAFFIC_GENERATE_OPERATION = "traffic.generate"
TRAFFIC_GENERATION_COMPLETED_EVENT = "traffic.generation.completed"


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
    fast: bool = False


def main() -> None:
    """Parse CLI input, invoke the bound operation, and render its summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario")
    parser.add_argument("--count", dest="request_count", type=int)
    parser.add_argument("--run-id")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="skip request pacing and the post-run collection wait",
    )
    command = TrafficCommandDto.model_validate(vars(parser.parse_args()))
    runtime = bootstrap()
    try:
        plan = runtime.plans.get(command.scenario)
        if plan is None:
            raise ValueError(f"unknown traffic scenario: {command.scenario}")
        if command.fast:
            plan = replace(
                plan,
                interval_seconds=0,
                collection_wait_seconds=0,
            )
        with runtime.telemetry.run_scope(
            TRAFFIC_GENERATE_OPERATION,
            run_id=command.run_id,
            scenario=command.scenario,
        ) as context:
            assert context.run_id is not None
            responses = runtime.run(
                plan,
                command.request_count,
                run_id=context.run_id,
            )
            runtime.telemetry.event(
                TRAFFIC_GENERATION_COMPLETED_EVENT,
                attributes={
                    "request_count": len(responses),
                },
            )
    finally:
        runtime.telemetry.shutdown()
    print(
        {
            "run_id": context.run_id,
            "status_codes": dict(
                Counter(response.status_code for response in responses)
            ),
        }
    )
