"""Generate deterministic valid, shifted, and invalid API traffic."""

import random
import time

from traffic_generator.domain import ScenarioMode, TrafficPlan, TrafficResponse
from traffic_generator.ports import PatientPool, PredictionClient, TrafficRecorder


class GenerateTraffic:
    def __init__(
        self,
        *,
        random_seed: int,
        pool: PatientPool,
        client: PredictionClient,
        recorder: TrafficRecorder,
    ) -> None:
        self._random_seed = random_seed
        self._pool = pool
        self._client = client
        self._recorder = recorder

    def execute(
        self, plan: TrafficPlan, *, request_count: int | None = None
    ) -> tuple[TrafficResponse, ...]:
        count = request_count or plan.request_count
        if count < 1:
            raise ValueError("traffic request count must be positive")
        rng = random.Random(f"{self._random_seed}:{plan.name}")
        responses: list[TrafficResponse] = []
        for index in range(count):
            features = self._pool.patient(rng.randrange(self._pool.size))
            if plan.mode is ScenarioMode.SHIFT:
                features = _apply_shift(features, plan)
            elif plan.mode is ScenarioMode.INVALID:
                features = _apply_invalid(
                    features, plan.invalid_cases[index % len(plan.invalid_cases)]
                )
            request_id = f"{plan.name}-{self._random_seed}-{index + 1:04d}"
            response = self._client.predict(
                features=features,
                request_id=request_id,
                scenario=plan.name,
                timeout_seconds=plan.timeout_seconds,
            )
            self._recorder.record(response)
            responses.append(response)
            if plan.interval_seconds:
                time.sleep(plan.interval_seconds)
        return tuple(responses)


def _apply_shift(features: dict[str, object], plan: TrafficPlan) -> dict[str, object]:
    shifted = dict(features)
    for transform in plan.transforms:
        value = shifted.get(transform.feature)
        if value is None:
            continue
        number = float(value) * transform.multiply + transform.add
        if transform.minimum is not None:
            number = max(number, transform.minimum)
        if transform.maximum is not None:
            number = min(number, transform.maximum)
        shifted[transform.feature] = number
    return shifted


def _apply_invalid(features: dict[str, object], case: str) -> dict[str, object]:
    invalid = dict(features)
    if case == "missing_feature":
        invalid.pop(next(iter(invalid)))
    elif case == "extra_feature":
        invalid["unexpected_feature"] = 1.0
    elif case == "wrong_boolean_type":
        boolean_name = next(name for name in invalid if name.endswith("__missing"))
        invalid[boolean_name] = "not-a-boolean"
    else:
        raise ValueError(f"unsupported invalid traffic case: {case}")
    return invalid
