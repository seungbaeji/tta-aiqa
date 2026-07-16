"""Generate deterministic valid, shifted, and invalid API traffic."""

import random
from collections.abc import Callable

from traffic_generator.domain import (
    ScenarioMode,
    TrafficPlan,
    TrafficResponse,
    apply_feature_transforms,
    apply_invalid_traffic_case,
)
from traffic_generator.ports import PatientPool, PredictionClient, TrafficRecorder


def generate_traffic(
    plan: TrafficPlan,
    request_count: int | None = None,
    *,
    random_seed: int,
    pool: PatientPool,
    client: PredictionClient,
    recorder: TrafficRecorder,
    sleep: Callable[[float], None],
) -> tuple[TrafficResponse, ...]:
    """Send one deterministic traffic plan through the configured prediction client."""
    count = plan.request_count if request_count is None else request_count
    if count < 1:
        raise ValueError("traffic request count must be positive")
    rng = random.Random(f"{random_seed}:{plan.name}")
    responses: list[TrafficResponse] = []
    for index in range(count):
        features = pool.patient(rng.randrange(pool.size))
        if plan.mode is ScenarioMode.SHIFT:
            features = apply_feature_transforms(features, plan.transforms)
        elif plan.mode is ScenarioMode.INVALID:
            features = apply_invalid_traffic_case(
                features, plan.invalid_cases[index % len(plan.invalid_cases)]
            )
        request_id = f"{plan.name}-{random_seed}-{index + 1:04d}"
        response = client.predict(
            features=features,
            request_id=request_id,
            scenario=plan.name,
            timeout_seconds=plan.timeout_seconds,
        )
        recorder.record(response)
        responses.append(response)
        if plan.interval_seconds:
            sleep(plan.interval_seconds)
    return tuple(responses)
