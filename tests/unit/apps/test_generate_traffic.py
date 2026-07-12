"""Deterministic traffic scenario use case tests."""

from dataclasses import dataclass, field

from traffic_generator.application import generate_traffic
from traffic_generator.domain import (
    FeatureTransform,
    InvalidTrafficCase,
    ScenarioMode,
    TrafficPlan,
    TrafficResponse,
)


@dataclass
class Pool:
    patients: tuple[dict[str, object], ...]

    @property
    def size(self) -> int:
        return len(self.patients)

    def patient(self, index: int) -> dict[str, object]:
        return dict(self.patients[index])


@dataclass
class Client:
    calls: list[tuple[dict[str, object], str, str]] = field(default_factory=list)

    def predict(
        self,
        *,
        features: dict[str, object],
        request_id: str,
        scenario: str,
        timeout_seconds: float,
    ) -> TrafficResponse:
        self.calls.append((features, request_id, scenario))
        return TrafficResponse(request_id, scenario, 200, 0.01, {"ok": True})


@dataclass
class Recorder:
    responses: list[TrafficResponse] = field(default_factory=list)

    def record(self, response: TrafficResponse) -> None:
        self.responses.append(response)


def generate(
    client: Client, recorder: Recorder, plan: TrafficPlan
) -> tuple[TrafficResponse, ...]:
    return generate_traffic(
        plan,
        random_seed=43,
        pool=Pool(
            (
                {"age": 50.0, "heart_rate": 80.0, "age__missing": False},
                {"age": 70.0, "heart_rate": 100.0, "age__missing": False},
            )
        ),
        client=client,
        recorder=recorder,
        sleep=lambda _: None,
    )


def test_shift_scenario_is_deterministic_and_applies_bounds() -> None:
    plan = TrafficPlan(
        name="current-shift",
        mode=ScenarioMode.SHIFT,
        request_count=2,
        interval_seconds=0,
        timeout_seconds=1,
        transforms=(
            FeatureTransform("age", add=80, maximum=120),
            FeatureTransform("heart_rate", multiply=1.5),
        ),
    )
    first_client, second_client = Client(), Client()

    generate(first_client, Recorder(), plan)
    generate(second_client, Recorder(), plan)

    assert first_client.calls == second_client.calls
    assert all(call[0]["age"] == 120 for call in first_client.calls)
    assert all(call[0]["heart_rate"] in {120.0, 150.0} for call in first_client.calls)


def test_invalid_scenario_cycles_contract_failures_and_records_responses() -> None:
    client, recorder = Client(), Recorder()
    plan = TrafficPlan(
        name="invalid",
        mode=ScenarioMode.INVALID,
        request_count=3,
        interval_seconds=0,
        timeout_seconds=1,
        invalid_cases=(
            InvalidTrafficCase.MISSING_FEATURE,
            InvalidTrafficCase.EXTRA_FEATURE,
            InvalidTrafficCase.WRONG_BOOLEAN_TYPE,
        ),
    )

    responses = generate(client, recorder, plan)

    assert len(client.calls[0][0]) == 2
    assert "unexpected_feature" in client.calls[1][0]
    assert client.calls[2][0]["age__missing"] == "not-a-boolean"
    assert tuple(recorder.responses) == responses


def test_use_case_controls_sleep_and_zero_count_override() -> None:
    """Timing is a collaborator and an explicit zero override is never hidden."""
    plan = TrafficPlan(
        name="baseline",
        mode=ScenarioMode.VALID,
        request_count=1,
        interval_seconds=0.25,
        timeout_seconds=1,
    )
    client, recorder = Client(), Recorder()
    delays: list[float] = []

    responses = generate_traffic(
        plan,
        random_seed=43,
        pool=Pool(({"age": 50.0, "age__missing": False},)),
        client=client,
        recorder=recorder,
        sleep=delays.append,
    )

    assert len(responses) == 1
    assert delays == [0.25]
    try:
        generate_traffic(
            plan,
            0,
            random_seed=43,
            pool=Pool(({"age": 50.0, "age__missing": False},)),
            client=client,
            recorder=recorder,
            sleep=delays.append,
        )
    except ValueError as error:
        assert str(error) == "traffic request count must be positive"
    else:
        raise AssertionError("explicit zero traffic override must be rejected")
