"""Composition root for the Traffic Generator."""

from dataclasses import dataclass

from aiqa_core.adapters.config import load_feature_contract
from aiqa_observability import Telemetry, create_telemetry, load_telemetry_policy

from traffic_generator.adapters import (
    CsvPatientPool,
    JsonlTrafficRecorder,
    RequestsPredictionClient,
    load_traffic_config,
)
from traffic_generator.application import GenerateTraffic
from traffic_generator.domain import TrafficPlan
from traffic_generator.settings import TrafficSettings


@dataclass(frozen=True)
class TrafficRuntime:
    plans: dict[str, TrafficPlan]
    use_case: GenerateTraffic
    telemetry: Telemetry


def bootstrap(**overrides: object) -> TrafficRuntime:
    settings = TrafficSettings(**overrides)
    config = load_traffic_config(settings.scenarios_path)
    feature_set = load_feature_contract(settings.feature_contract_path)
    return TrafficRuntime(
        plans=config.plans(),
        use_case=GenerateTraffic(
            random_seed=config.random_seed,
            pool=CsvPatientPool(settings.patient_pool_path, feature_set),
            client=RequestsPredictionClient(str(settings.api_url)),
            recorder=JsonlTrafficRecorder(settings.response_artifact_path),
        ),
        telemetry=create_telemetry(
            service_name="traffic-generator",
            environment=settings.environment,
            policy=load_telemetry_policy(settings.telemetry_config_path),
            otlp_endpoint=(
                str(settings.otlp_endpoint) if settings.otlp_endpoint else None
            ),
        ),
    )
