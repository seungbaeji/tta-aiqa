"""Deterministic traffic scenario use case tests."""

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from aiqa_observability import is_valid_correlation_id
from traffic_generator.application import (
    collect_course_session,
    generate_traffic,
    update_signal_availability,
)
from traffic_generator.domain import (
    CollectionModelIdentity,
    CollectionSession,
    FeatureTransform,
    InvalidTrafficCase,
    ScenarioCollection,
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

    def record_id(self, index: int) -> str:
        return f"pool-{index}"


@dataclass
class Client:
    calls: list[tuple[dict[str, object], str, str, str]] = field(default_factory=list)

    def predict(
        self,
        *,
        features: dict[str, object],
        request_id: str,
        run_id: str,
        scenario: str,
        record_id: str,
        timeout_seconds: float,
    ) -> TrafficResponse:
        self.calls.append((features, request_id, run_id, scenario))
        return TrafficResponse(
            request_id=request_id,
            run_id=run_id,
            scenario=scenario,
            record_id=record_id,
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

    assert [call[0]["age"] for call in baseline_client.calls] == [
        call[0]["age"] - 10 for call in shifted_client.calls
    ]
    assert [response.request_id for response in baseline_responses] != [
        response.request_id for response in shifted_responses
    ]
    assert {response.run_id for response in baseline_responses} == {"run-baseline"}
    assert {response.run_id for response in shifted_responses} == {"run-shifted"}
    assert {response.record_id for response in baseline_responses} <= {
        "pool-0",
        "pool-1",
    }
    assert [response.record_id for response in baseline_responses] == [
        response.record_id for response in shifted_responses
    ]


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


def test_course_session_collects_three_scenarios_with_a_stable_handoff() -> None:
    plans = {
        name: TrafficPlan(
            name=name,
            mode=ScenarioMode.INVALID if name == "invalid" else ScenarioMode.VALID,
            request_count=1,
            interval_seconds=0,
            timeout_seconds=1,
            invalid_cases=(
                (InvalidTrafficCase.MISSING_FEATURE,) if name == "invalid" else ()
            ),
        )
        for name in ("baseline", "current-shift", "invalid")
    }
    moments = iter(datetime(2026, 7, 27, 5, minute, tzinfo=UTC) for minute in range(8))
    calls: list[tuple[str, str]] = []

    def execute(plan: TrafficPlan, run_id: str) -> tuple[TrafficResponse, ...]:
        calls.append((plan.name, run_id))
        if plan.name == "invalid":
            return (
                TrafficResponse(
                    request_id=f"{plan.name}-{run_id}-0001",
                    run_id=run_id,
                    scenario=plan.name,
                    status_code=422,
                    elapsed_seconds=0.01,
                    body={"detail": {"code": "MODEL_INPUT_INVALID"}},
                ),
            )
        return (
            TrafficResponse(
                request_id=f"{plan.name}-{run_id}-0001",
                run_id=run_id,
                scenario=plan.name,
                status_code=200,
                elapsed_seconds=0.01,
                body={
                    "model_profile": "baseline",
                    "model_version": "baseline-f2576f12512a",
                    "threshold": 0.5,
                },
            ),
        )

    session = collect_course_session(
        plans,
        execute=execute,
        session_id="class-session-01",
        environment="compose",
        scope="local",
        artifact_path=Path("/runtime/artifacts/traffic/compose.jsonl"),
        manifest_path=Path("/runtime/artifacts/traffic/collection-session.json"),
        now=lambda: next(moments),
    )

    assert [name for name, _ in calls] == [
        "baseline",
        "current-shift",
        "invalid",
    ]
    assert len({run_id for _, run_id in calls}) == 3
    assert all(is_valid_correlation_id(run_id) for _, run_id in calls)
    assert session.as_document() == {
        "schema_version": 1,
        "session_id": "class-session-01",
        "started_at": "2026-07-27T05:00:00Z",
        "completed_at": "2026-07-27T05:07:00Z",
        "environment": "compose",
        "scope": "local",
        "dashboard_url": None,
        "signal_availability": {
            "prometheus": {
                "status": "not_checked",
                "checked_at": None,
            },
            "loki": {
                "status": "not_checked",
                "checked_at": None,
            },
            "tempo": {
                "status": "not_checked",
                "checked_at": None,
            },
        },
        "model_identity": {
            "profile": "baseline",
            "version": "baseline-f2576f12512a",
            "threshold": 0.5,
        },
        "manifest_path": ("/runtime/artifacts/traffic/collection-session.json"),
        "scenarios": [
            {
                "name": "baseline",
                "run_id": calls[0][1],
                "started_at": "2026-07-27T05:01:00Z",
                "completed_at": "2026-07-27T05:02:00Z",
                "status_counts": {"200": 1},
                "artifact_path": "/runtime/artifacts/traffic/compose.jsonl",
            },
            {
                "name": "current-shift",
                "run_id": calls[1][1],
                "started_at": "2026-07-27T05:03:00Z",
                "completed_at": "2026-07-27T05:04:00Z",
                "status_counts": {"200": 1},
                "artifact_path": "/runtime/artifacts/traffic/compose.jsonl",
            },
            {
                "name": "invalid",
                "run_id": calls[2][1],
                "started_at": "2026-07-27T05:05:00Z",
                "completed_at": "2026-07-27T05:06:00Z",
                "status_counts": {"422": 1},
                "artifact_path": "/runtime/artifacts/traffic/compose.jsonl",
            },
        ],
    }


def test_course_session_rejects_a_model_change_between_scenarios() -> None:
    plans = {
        name: TrafficPlan(
            name=name,
            mode=ScenarioMode.INVALID if name == "invalid" else ScenarioMode.VALID,
            request_count=1,
            interval_seconds=0,
            timeout_seconds=1,
            invalid_cases=(
                (InvalidTrafficCase.MISSING_FEATURE,) if name == "invalid" else ()
            ),
        )
        for name in ("baseline", "current-shift", "invalid")
    }

    def execute(plan: TrafficPlan, run_id: str) -> tuple[TrafficResponse, ...]:
        version = (
            "unexpected-model"
            if plan.name == "current-shift"
            else "baseline-f2576f12512a"
        )
        return (
            TrafficResponse(
                request_id=f"{plan.name}-{run_id}-0001",
                run_id=run_id,
                scenario=plan.name,
                status_code=200,
                elapsed_seconds=0.01,
                body={
                    "model_profile": "baseline",
                    "model_version": version,
                    "threshold": 0.5,
                },
            ),
        )

    with pytest.raises(ValueError, match="model identity changed"):
        collect_course_session(
            plans,
            execute=execute,
            session_id="class-session-01",
            environment="compose",
            scope="local",
            artifact_path=Path("artifacts/traffic/compose.jsonl"),
            manifest_path=Path("artifacts/traffic/collection-session.json"),
        )


def test_signal_availability_updates_only_explicitly_checked_backends() -> None:
    session = CollectionSession(
        session_id="class-session-01",
        started_at="2026-07-27T05:00:00Z",
        completed_at="2026-07-27T05:07:00Z",
        environment="compose",
        scope="local",
        model_identity=CollectionModelIdentity(
            profile="baseline",
            version="baseline-f2576f12512a",
            threshold=0.5,
        ),
        manifest_path=Path("artifacts/traffic/collection-session.json"),
        scenarios=tuple(
            ScenarioCollection(
                name=name,
                run_id=f"class-session-01-{name}",
                started_at=f"2026-07-27T05:0{index}:00Z",
                completed_at=f"2026-07-27T05:0{index + 1}:00Z",
                status_counts=((422, 1),) if name == "invalid" else ((200, 1),),
                artifact_path=Path("artifacts/traffic/compose.jsonl"),
            )
            for index, name in enumerate(
                ("baseline", "current-shift", "invalid"),
                start=1,
            )
        ),
    )

    updated = update_signal_availability(
        session,
        statuses={
            "prometheus": "available",
            "loki": "unavailable",
        },
        dashboard_url=(
            "https://example.grafana.net/d/tta-aiqa-quality/service-quality"
        ),
        now=lambda: datetime(2026, 7, 27, 5, 10, tzinfo=UTC),
    )

    assert updated.session_id == session.session_id
    assert updated.dashboard_url == (
        "https://example.grafana.net/d/tta-aiqa-quality/service-quality"
    )
    assert updated.as_document()["signal_availability"] == {
        "prometheus": {
            "status": "available",
            "checked_at": "2026-07-27T05:10:00Z",
        },
        "loki": {
            "status": "unavailable",
            "checked_at": "2026-07-27T05:10:00Z",
        },
        "tempo": {
            "status": "not_checked",
            "checked_at": None,
        },
    }
    assert session.as_document()["signal_availability"]["prometheus"] == {
        "status": "not_checked",
        "checked_at": None,
    }
    with pytest.raises(ValueError, match="must be available or unavailable"):
        update_signal_availability(
            updated,
            statuses={"prometheus": "not_checked"},
        )
    with pytest.raises(
        ValueError,
        match="signal check time must not precede session completion",
    ):
        update_signal_availability(
            session,
            statuses={"tempo": "available"},
            now=lambda: datetime(2026, 7, 27, 5, 6, tzinfo=UTC),
        )


def test_collection_manifest_rejects_reversed_or_uncontained_time_ranges() -> None:
    with pytest.raises(ValueError, match="completion must not precede start"):
        ScenarioCollection(
            name="baseline",
            run_id="class-session-01-baseline",
            started_at="2026-07-27T05:02:00Z",
            completed_at="2026-07-27T05:01:00Z",
            status_counts=((200, 1),),
            artifact_path=Path("artifacts/traffic/compose.jsonl"),
        )

    scenarios = tuple(
        ScenarioCollection(
            name=name,
            run_id=f"class-session-01-{name}",
            started_at=f"2026-07-27T05:0{index}:00Z",
            completed_at=f"2026-07-27T05:0{index + 1}:00Z",
            status_counts=((422, 1),) if name == "invalid" else ((200, 1),),
            artifact_path=Path("artifacts/traffic/compose.jsonl"),
        )
        for index, name in enumerate(
            ("baseline", "current-shift", "invalid"),
            start=1,
        )
    )
    with pytest.raises(
        ValueError,
        match="collection session completion must not precede start",
    ):
        CollectionSession(
            session_id="class-session-01",
            started_at="2026-07-27T05:08:00Z",
            completed_at="2026-07-27T05:07:00Z",
            environment="compose",
            scope="local",
            model_identity=CollectionModelIdentity(
                profile="baseline",
                version="baseline-f2576f12512a",
                threshold=0.5,
            ),
            manifest_path=Path("artifacts/traffic/collection-session.json"),
            scenarios=scenarios,
        )
    with pytest.raises(ValueError, match="must contain every scenario range"):
        CollectionSession(
            session_id="class-session-01",
            started_at="2026-07-27T05:02:00Z",
            completed_at="2026-07-27T05:07:00Z",
            environment="compose",
            scope="local",
            model_identity=CollectionModelIdentity(
                profile="baseline",
                version="baseline-f2576f12512a",
                threshold=0.5,
            ),
            manifest_path=Path("artifacts/traffic/collection-session.json"),
            scenarios=scenarios,
        )
    overlapping = (
        scenarios[0],
        replace(
            scenarios[1],
            started_at="2026-07-27T05:01:30Z",
        ),
        scenarios[2],
    )
    with pytest.raises(
        ValueError,
        match="scenario ranges must be ordered and non-overlapping",
    ):
        CollectionSession(
            session_id="class-session-01",
            started_at="2026-07-27T05:00:00Z",
            completed_at="2026-07-27T05:07:00Z",
            environment="compose",
            scope="local",
            model_identity=CollectionModelIdentity(
                profile="baseline",
                version="baseline-f2576f12512a",
                threshold=0.5,
            ),
            manifest_path=Path("artifacts/traffic/collection-session.json"),
            scenarios=overlapping,
        )
