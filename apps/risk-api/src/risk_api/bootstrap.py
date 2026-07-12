"""Composition root for the Risk API."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

from aiqa_core.adapters.config import load_feature_contract
from aiqa_observability import (
    Telemetry,
    create_telemetry,
    load_telemetry_policy,
)
from aiqa_observability.adapters import instrument_fastapi
from aiqa_serving.adapters import (
    KServeRiskScorer,
    LocalSklearnRiskScorer,
)
from aiqa_serving.application import predict_risk
from aiqa_serving.domain import (
    ModelIdentity,
    PredictionLabels,
    PredictionRequest,
    RiskPrediction,
)
from aiqa_serving.ports import RiskScorer
from fastapi import FastAPI

from risk_api.config import load_api_config
from risk_api.http import build_http_app
from risk_api.settings import RiskApiSettings
from risk_api.telemetry import PredictionTelemetryRecorder, RiskApiTelemetry


def build_application(settings: RiskApiSettings) -> FastAPI:
    """Assemble the Risk API delivery adapter and its serving operation."""
    api_config = load_api_config(settings.api_config_path)
    feature_set = load_feature_contract(settings.feature_contract_path)
    contract_hash = _sha256(settings.feature_contract_path)
    telemetry_policy = load_telemetry_policy(settings.telemetry_config_path)
    telemetry = RiskApiTelemetry(
        create_telemetry(
            service_name="risk-api",
            environment=settings.environment,
            policy=telemetry_policy,
            otlp_endpoint=(
                str(settings.otlp_endpoint) if settings.otlp_endpoint else None
            ),
        ),
        api_config.observability,
    )
    scorer: RiskScorer
    reload_operation: Callable[[], ModelIdentity] | None = None
    if settings.model_backend == "local":
        assert settings.model_bundle_path is not None
        scorer = LocalSklearnRiskScorer(settings.model_bundle_path, contract_hash)
        reload_operation = scorer.reload
    else:
        assert settings.kserve_url is not None
        assert settings.kserve_model_name is not None
        assert settings.model_metadata_path is not None
        metadata = json.loads(settings.model_metadata_path.read_text(encoding="utf-8"))
        if metadata["feature_contract"]["sha256"] != contract_hash:
            raise ValueError("KServe metadata feature contract hash mismatch")
        scorer = KServeRiskScorer(
            endpoint=str(settings.kserve_url),
            model_name=settings.kserve_model_name,
            feature_names=feature_set.feature_names,
            identity=ModelIdentity(
                profile=metadata["profile"],
                version=f"{metadata['profile']}-{metadata['model_sha256'][:12]}",
                threshold=float(metadata["threshold"]),
            ),
            headers_provider=_kserve_request_headers(
                telemetry.platform, api_config.request_id_header
            ),
        )
    recorder = PredictionTelemetryRecorder(telemetry)
    labels = PredictionLabels(
        positive=api_config.positive_label,
        negative=api_config.negative_label,
    )

    def predict(request: PredictionRequest) -> RiskPrediction:
        return predict_risk(
            request,
            feature_set=feature_set,
            scorer=scorer,
            event_recorder=recorder,
            labels=labels,
        )

    app = build_http_app(
        config=api_config,
        feature_count=len(feature_set.features),
        predict_operation=predict,
        scorer=scorer,
        backend=settings.model_backend,
        reload_operation=reload_operation,
        telemetry=telemetry,
    )
    instrument_fastapi(app, telemetry.platform.tracing)
    return app


def bootstrap(**overrides: object) -> FastAPI:
    """Build the Risk API from Pydantic runtime settings."""
    return build_application(RiskApiSettings(**overrides))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _kserve_request_headers(
    telemetry: Telemetry, request_id_header: str
) -> Callable[[], dict[str, str]]:
    """Build outbound KServe headers from the current API request context."""

    def headers() -> dict[str, str]:
        return telemetry.outbound_request_headers(request_id_header)

    return headers
