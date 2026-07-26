"""Deterministic traffic scenario use case tests."""

from dataclasses import dataclass, field

from aiqa_observability import is_valid_correlation_id
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
    calls: list[tuple[dict[str, object], str, str, str]] = field(
        default_factory=list
    )

    def predict(
        self,
        *,
        features: dict[str, object],
        request_id: str,
        run_id: str,
        scenario: str,
        timeout_seconds: float,
    ) -> TrafficResponse:
        self.calls.append((features, request_id, run_id, scenario))
        return TrafficResponse(
            request_id=request_id,
            run_id=run_id,
            scenario=scenario,
            status_code=200,
            elapsed_seconds=0.01,
            body={"ok": True},
        )


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
        run_id="run-a",
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


def test_scenarios_share_samples_while_run_ids_keep_reruns_distinct() -> None:
    baseline = TrafficPlan(
        name="baseline",
        mode=ScenarioMode.VALID,
        request_count=2,
        interval_seconds=0,
        timeout_seconds=1,
    )
    shifted = TrafficPlan(
        name="current-shift",
        mode=ScenarioMode.SHIFT,
        request_count=2,
        interval_seconds=0,
        timeout_seconds=1,
        transforms=(FeatureTransform("age", add=10),),
    )
    baseline_client, shifted_client = Client(), Client()
    pool = Pool(
        (
            {"age": 50.0, "age__missing": False},
            {"age": 70.0, "age__missing": False},
        )
    )

    baseline_responses = generate_traffic(
        baseline,
        run_id="run-baseline",
        random_seed=43,
        pool=pool,
        client=baseline_client,
        recorder=Recorder(),
        sleep=lambda _: None,
    )
    shifted_responses = generate_traffic(
        shifted,
        run_id="run-shifted",
        random_seed=43,
        pool=pool,
        client=shifted_client,
        recorder=Recorder(),
        sleep=lambda _: None,
    )

    assert [
        call[0]["age"] for call in baseline_client.calls
    ] == [call[0]["age"] - 10 for call in shifted_client.calls]
    assert [response.request_id for response in baseline_responses] != [
        response.request_id for response in shifted_responses
    ]
    assert {response.run_id for response in baseline_responses} == {"run-baseline"}
    assert {response.run_id for response in shifted_responses} == {"run-shifted"}


def test_same_scenario_rerun_preserves_samples_but_not_request_ids() -> None:
    plan = TrafficPlan(
        name="baseline",
        mode=ScenarioMode.VALID,
        request_count=2,
        interval_seconds=0,
        timeout_seconds=1,
    )
    first, second = Client(), Client()
    pool = Pool(
        (
            {"age": 50.0, "age__missing": False},
            {"age": 70.0, "age__missing": False},
        )
    )

    for run_id, client in (("run-one", first), ("run-two", second)):
        generate_traffic(
            plan,
            run_id=run_id,
            random_seed=43,
            pool=pool,
            client=client,
            recorder=Recorder(),
            sleep=lambda _: None,
        )

    assert [call[0] for call in first.calls] == [call[0] for call in second.calls]
    assert [call[1] for call in first.calls] != [call[1] for call in second.calls]


def test_max_length_run_ids_preserve_samples_and_generate_distinct_safe_ids() -> None:
    """Full run identity survives deterministic shortening at the 64-char boundary."""
    plan = TrafficPlan(
        name="baseline",
        mode=ScenarioMode.VALID,
        request_count=2,
        interval_seconds=0,
        timeout_seconds=1,
    )
    pool = Pool(
        (
            {"age": 50.0, "age__missing": False},
            {"age": 70.0, "age__missing": False},
        )
    )
    first_run_id = f"{'r' * 63}a"
    second_run_id = f"{'r' * 63}b"
    first, replay, second = Client(), Client(), Client()

    for run_id, client in (
        (first_run_id, first),
        (first_run_id, replay),
        (second_run_id, second),
    ):
        generate_traffic(
            plan,
            run_id=run_id,
            random_seed=43,
            pool=pool,
            client=client,
            recorder=Recorder(),
            sleep=lambda _: None,
        )

    first_features = [call[0] for call in first.calls]
    first_request_ids = [call[1] for call in first.calls]
    assert first_features == [call[0] for call in replay.calls]
    assert first_features == [call[0] for call in second.calls]
    assert first_request_ids == [call[1] for call in replay.calls]
    assert first_request_ids != [call[1] for call in second.calls]
    assert all(len(request_id) <= 64 for request_id in first_request_ids)
    assert all(is_valid_correlation_id(request_id) for request_id in first_request_ids)


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
        run_id="run-a",
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
            run_id="run-a",
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
