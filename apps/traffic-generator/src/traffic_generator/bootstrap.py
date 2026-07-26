"""Composition root for the Traffic Generator."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from time import sleep

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
    run: Callable[[TrafficPlan, int | None, str], tuple[TrafficResponse, ...]]
    telemetry: Telemetry
    environment: str
    response_artifact_path: Path
    portable_response_artifact_path: Path = Path("artifacts/traffic/compose.jsonl")
    portable_manifest_path: Path = Path("artifacts/traffic/collection-session.json")


def bootstrap(**overrides: object) -> TrafficRuntime:
    """Assemble concrete Traffic Generator adapters for one process."""
    settings = TrafficSettings(**overrides)
    config = load_traffic_config(settings.scenarios_path)
    feature_set = load_feature_contract(settings.feature_contract_path)
    pool = CsvPatientPool(settings.patient_pool_path, feature_set)
    telemetry = create_telemetry(
        service_name="traffic-generator",
        environment=settings.environment,
        policy=load_telemetry_policy(settings.telemetry_config_path),
        otlp_endpoint=(str(settings.otlp_endpoint) if settings.otlp_endpoint else None),
    )
    client = RequestsPredictionClient(
        str(settings.api_url),
        telemetry=telemetry,
    )
    recorder = JsonlTrafficRecorder(settings.response_artifact_path)

    return TrafficRuntime(
        plans=config.plans(),
        run=partial(
            generate_traffic,
            random_seed=config.random_seed,
            pool=pool,
            client=client,
            recorder=recorder,
            sleep=sleep,
        ),
        telemetry=telemetry,
        environment=settings.environment,
        response_artifact_path=settings.response_artifact_path,
        portable_response_artifact_path=settings.portable_response_artifact_path,
        portable_manifest_path=settings.portable_manifest_path,
    )
