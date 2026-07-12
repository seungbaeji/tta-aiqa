"""CLI entry point for deterministic traffic scenarios."""

import argparse
from collections import Counter

from pydantic import BaseModel, ConfigDict, Field

from traffic_generator.bootstrap import bootstrap


class TrafficCommandDto(BaseModel):
    """Validated command-line input for one traffic generation run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario: str
    request_count: int | None = Field(default=None, gt=0)


def main() -> None:
    """Parse CLI input, invoke the bound operation, and render its summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario",
        choices=("baseline", "approved-candidate", "current-shift", "invalid"),
    )
    parser.add_argument("--count", dest="request_count", type=int)
    command = TrafficCommandDto.model_validate(vars(parser.parse_args()))
    runtime = bootstrap()
    try:
        with runtime.telemetry.run_scope(
            "traffic.generate", scenario=command.scenario
        ):
            responses = runtime.run(
                runtime.plans[command.scenario], command.request_count
            )
            runtime.telemetry.event(
                "traffic.generation.completed",
                attributes={
                    "request_count": len(responses),
                },
            )
    finally:
        runtime.telemetry.shutdown()
    print(dict(Counter(response.status_code for response in responses)))
