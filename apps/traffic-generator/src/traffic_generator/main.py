"""CLI entry point for deterministic traffic scenarios."""

import argparse
from collections import Counter

from pydantic import BaseModel, ConfigDict, Field

from traffic_generator.bootstrap import bootstrap

TRAFFIC_GENERATE_OPERATION = "traffic.generate"
TRAFFIC_GENERATION_COMPLETED_EVENT = "traffic.generation.completed"


class TrafficCommandDto(BaseModel):
    """Validated command-line input for one traffic generation run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario: str = Field(min_length=1)
    request_count: int | None = Field(default=None, gt=0)


def main() -> None:
    """Parse CLI input, invoke the bound operation, and render its summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario")
    parser.add_argument("--count", dest="request_count", type=int)
    command = TrafficCommandDto.model_validate(vars(parser.parse_args()))
    runtime = bootstrap()
    try:
        plan = runtime.plans.get(command.scenario)
        if plan is None:
            raise ValueError(f"unknown traffic scenario: {command.scenario}")
        with runtime.telemetry.run_scope(
            TRAFFIC_GENERATE_OPERATION,
            scenario=command.scenario,
        ):
            responses = runtime.run(plan, command.request_count)
            runtime.telemetry.event(
                TRAFFIC_GENERATION_COMPLETED_EVENT,
                attributes={
                    "request_count": len(responses),
                },
            )
    finally:
        runtime.telemetry.shutdown()
    print(dict(Counter(response.status_code for response in responses)))
