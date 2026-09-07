"""Generate deterministic valid, shifted, and invalid API traffic."""

import hashlib
import random
from collections.abc import Callable

from aiqa_observability import (
    CORRELATION_ID_MAX_LENGTH,
    is_valid_correlation_id,
)

from traffic_generator.domain import (
    ScenarioMode,
    TrafficPlan,
    TrafficResponse,
    apply_feature_transforms,
    apply_invalid_traffic_case,
)
from traffic_generator.ports import PatientPool, PredictionClient, TrafficRecorder

REQUEST_ID_DIGEST_LENGTH = 32


def build_request_id(*, scenario: str, run_id: str, sequence: int) -> str:
    """Build one deterministic, API-safe ID without losing full-run distinction."""
    if sequence < 1:
        raise ValueError("traffic request sequence must be positive")
    if not is_valid_correlation_id(scenario):
        raise ValueError("traffic scenario must match the correlation ID contract")
    if not is_valid_correlation_id(run_id):
        raise ValueError("traffic run ID must match the correlation ID contract")

    sequence_token = f"{sequence:04d}"
    readable = f"{scenario}-{run_id}"
    candidate = f"{readable}-{sequence_token}"
    if len(candidate) <= CORRELATION_ID_MAX_LENGTH:
        return candidate

    digest = hashlib.sha256(
        f"{scenario}\0{run_id}".encode()
    ).hexdigest()[:REQUEST_ID_DIGEST_LENGTH]
    suffix = f"-h{digest}-{sequence_token}"
    readable_limit = CORRELATION_ID_MAX_LENGTH - len(suffix)
    if readable_limit < 1:
        raise ValueError("traffic request sequence exceeds the correlation ID contract")
    readable_prefix = readable[:readable_limit].rstrip("._-")
    request_id = f"{readable_prefix}{suffix}"
    if not is_valid_correlation_id(request_id):
        raise AssertionError("generated traffic request ID violated its wire contract")
    return request_id


def generate_traffic(
    plan: TrafficPlan,
    request_count: int | None = None,
    *,
    run_id: str,
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
    if not is_valid_correlation_id(run_id):
        raise ValueError("traffic run ID must match the correlation ID contract")
    rng = random.Random(random_seed)
    responses: list[TrafficResponse] = []
    for sequence in range(count):
        pool_index = rng.randrange(pool.size)
        features = pool.patient(pool_index)
        record_id = pool.record_id(pool_index)
        if plan.mode is ScenarioMode.SHIFT:
            features = apply_feature_transforms(features, plan.transforms)
        elif plan.mode is ScenarioMode.INVALID:
            features = apply_invalid_traffic_case(
                features, plan.invalid_cases[sequence % len(plan.invalid_cases)]
            )
        request_id = build_request_id(
            scenario=plan.name,
            run_id=run_id,
            sequence=sequence + 1,
        )
        response = client.predict(
            features=features,
            request_id=request_id,
            run_id=run_id,
            scenario=plan.name,
            record_id=record_id,
            timeout_seconds=plan.timeout_seconds,
        )
        recorder.record(response)
        responses.append(response)
        if plan.interval_seconds:
            sleep(plan.interval_seconds)
    if plan.collection_wait_seconds:
        sleep(plan.collection_wait_seconds)
    return tuple(responses)
