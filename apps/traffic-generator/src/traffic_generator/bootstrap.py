"""Composition root for the Traffic Generator."""

from collections.abc import Callable
from dataclasses import dataclass

from aiqa_core.adapters.config import load_feature_contract
from aiqa_observability import Telemetry, create_telemetry, load_telemetry_policy

from traffic_generator.adapters import (
    CsvPatientPool,
    JsonlTrafficRecorder,
    RequestsPredictionClient,
    load_traffic_config,
)
from traffic_generator.application import generate_traffic
from traffic_generator.domain import TrafficPlan, TrafficResponse
from traffic_generator.settings import TrafficSettings


@dataclass(frozen=True)
class TrafficRuntime:
    """Bound traffic operation and process resources for the CLI adapter."""

    plans: dict[str, TrafficPlan]
    run: Callable[[TrafficPlan, int | None], tuple[TrafficResponse, ...]]
    telemetry: Telemetry


def bootstrap(**overrides: object) -> TrafficRuntime:
    """Assemble concrete Traffic Generator adapters for one process."""
    settings = TrafficSettings(**overrides)
    config = load_traffic_config(settings.scenarios_path)
    feature_set = load_feature_contract(settings.feature_contract_path)
    pool = CsvPatientPool(settings.patient_pool_path, feature_set)
    client = RequestsPredictionClient(str(settings.api_url))
    recorder = JsonlTrafficRecorder(settings.response_artifact_path)

    def run(
        plan: TrafficPlan, request_count: int | None
    ) -> tuple[TrafficResponse, ...]:
        return generate_traffic(
            plan,
            random_seed=config.random_seed,
            pool=pool,
            client=client,
            recorder=recorder,
            request_count=request_count,
        )

    return TrafficRuntime(
        plans=config.plans(),
        run=run,
        telemetry=create_telemetry(
            service_name="traffic-generator",
            environment=settings.environment,
            policy=load_telemetry_policy(settings.telemetry_config_path),
            otlp_endpoint=(
                str(settings.otlp_endpoint) if settings.otlp_endpoint else None
            ),
        ),
    )
