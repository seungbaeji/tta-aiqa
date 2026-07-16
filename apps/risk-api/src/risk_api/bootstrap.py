"""Composition root for the Risk API."""

from __future__ import annotations

from functools import partial

from aiqa_core.adapters.config import load_feature_contract
from aiqa_observability import (
    create_telemetry,
    load_telemetry_policy,
)
from aiqa_observability.adapters import instrument_fastapi
from aiqa_serving.adapters import (
    KServeRiskScorer,
    LocalSklearnRiskScorer,
    sha256_file,
)
from aiqa_serving.application import predict_risk
from aiqa_serving.domain import PredictionLabels
from aiqa_serving.ports import RiskScorer
from fastapi import FastAPI

from risk_api.adapters import (
    PredictionTelemetryRecorder,
    RiskApiTelemetry,
    build_http_app,
    load_api_config,
    load_kserve_model_identity,
)
from risk_api.settings import RiskApiSettings


def build_application(settings: RiskApiSettings) -> FastAPI:
    """Assemble the Risk API delivery adapter and its serving operation."""
    api_config = load_api_config(settings.api_config_path)
    feature_set = load_feature_contract(settings.feature_contract_path)
    contract_hash = sha256_file(settings.feature_contract_path)
    telemetry_policy = load_telemetry_policy(settings.telemetry_config_path)
    platform = create_telemetry(
        service_name="risk-api",
        environment=settings.environment,
        policy=telemetry_policy,
        otlp_endpoint=(str(settings.otlp_endpoint) if settings.otlp_endpoint else None),
    )
    telemetry = RiskApiTelemetry(platform, api_config.observability)
    scorer: RiskScorer
    if settings.model_backend == "local":
        assert settings.model_bundle_path is not None
        scorer = LocalSklearnRiskScorer(settings.model_bundle_path, contract_hash)
    else:
        assert settings.kserve_url is not None
        assert settings.kserve_model_name is not None
        assert settings.model_metadata_path is not None
        identity = load_kserve_model_identity(
            settings.model_metadata_path,
            expected_feature_contract_sha256=contract_hash,
        )
        scorer = KServeRiskScorer(
            endpoint=str(settings.kserve_url),
            model_name=settings.kserve_model_name,
            feature_names=feature_set.feature_names,
            identity=identity,
            headers_provider=partial(
                platform.outbound_request_headers,
                api_config.request_id_header,
            ),
        )
    recorder = PredictionTelemetryRecorder(telemetry)
    labels = PredictionLabels(
        positive=api_config.positive_label,
        negative=api_config.negative_label,
    )

    app = build_http_app(
        config=api_config,
        feature_count=len(feature_set.features),
        predict_operation=partial(
            predict_risk,
            feature_set=feature_set,
            scorer=scorer,
            event_recorder=recorder,
            labels=labels,
        ),
        scorer=scorer,
        backend=settings.model_backend,
        telemetry=telemetry,
    )
    instrument_fastapi(app, platform.tracing)
    return app


def bootstrap(**overrides: object) -> FastAPI:
    """Build the Risk API from Pydantic runtime settings."""
    return build_application(RiskApiSettings(**overrides))
