"""CLI entry point for deterministic traffic scenarios."""

import argparse
from collections import Counter

from traffic_generator.bootstrap import bootstrap


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario",
        choices=("baseline", "approved-candidate", "current-shift", "invalid"),
    )
    parser.add_argument("--count", type=int)
    args = parser.parse_args()
    runtime = bootstrap()
    try:
        with runtime.telemetry.run_scope(
            "traffic.generate", scenario=args.scenario
        ):
            responses = runtime.use_case.execute(
                runtime.plans[args.scenario], request_count=args.count
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
