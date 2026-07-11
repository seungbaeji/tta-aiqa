"""Composition root for the Risk API."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aiqa_core.adapters.config import load_feature_contract
from aiqa_observability.adapters import (
    TelemetryRuntime,
    instrument_fastapi,
    load_telemetry_contract,
)
from aiqa_serving.adapters import (
    KServeRiskScorer,
    LocalSklearnRiskScorer,
)
from aiqa_serving.application import PredictRisk
from aiqa_serving.domain import ModelIdentity
from fastapi import FastAPI

from risk_api.config import load_api_config
from risk_api.http import build_http_app
from risk_api.settings import RiskApiSettings
from risk_api.telemetry import PredictionTelemetryRecorder


def build_application(settings: RiskApiSettings) -> FastAPI:
    api_config = load_api_config(settings.api_config_path)
    feature_set = load_feature_contract(settings.feature_contract_path)
    contract_hash = _sha256(settings.feature_contract_path)
    telemetry_contract = load_telemetry_contract(settings.telemetry_config_path)
    telemetry = TelemetryRuntime(telemetry_contract, settings.environment)
    if settings.model_backend == "local":
        assert settings.model_bundle_path is not None
        scorer = LocalSklearnRiskScorer(settings.model_bundle_path, contract_hash)
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
        )
    predict_risk = PredictRisk(
        feature_set, scorer, PredictionTelemetryRecorder(telemetry)
    )
    app = build_http_app(
        config=api_config,
        feature_set=feature_set,
        predict_risk=predict_risk,
        scorer=scorer,
        backend=settings.model_backend,
        telemetry=telemetry,
    )
    if settings.telemetry_enabled:
        instrument_fastapi(
            app,
            contract=telemetry_contract,
            environment=settings.environment,
            endpoint=str(settings.otlp_endpoint) if settings.otlp_endpoint else None,
        )
    return app


def bootstrap(**overrides: object) -> FastAPI:
    return build_application(RiskApiSettings(**overrides))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
