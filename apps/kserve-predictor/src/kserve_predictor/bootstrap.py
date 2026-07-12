"""Composition root for the KServe predictor process."""

import hashlib
from pathlib import Path

from aiqa_core.adapters.config import load_feature_contract
from aiqa_observability import create_telemetry, load_telemetry_policy
from aiqa_observability.adapters import instrument_fastapi
from aiqa_serving.adapters import LocalSklearnRiskScorer
from aiqa_serving.application import score_risk
from aiqa_serving.domain import PredictionRequest, ScoredRisk
from fastapi import FastAPI

from kserve_predictor.http import build_http_app
from kserve_predictor.settings import KServePredictorSettings


def build_application(settings: KServePredictorSettings) -> FastAPI:
    """Assemble the KServe V2 adapter around a bound scoring operation."""
    feature_set = load_feature_contract(settings.feature_contract_path)
    scorer = LocalSklearnRiskScorer(
        settings.model_bundle_path,
        _sha256(settings.feature_contract_path),
    )
    telemetry = create_telemetry(
        service_name="kserve-risk-predictor",
        environment=settings.environment,
        policy=load_telemetry_policy(settings.telemetry_config_path),
        otlp_endpoint=str(settings.otlp_endpoint) if settings.otlp_endpoint else None,
    )

    def score(request: PredictionRequest) -> ScoredRisk:
        return score_risk(request, feature_set=feature_set, scorer=scorer)

    app = build_http_app(
        model_name=settings.model_name,
        score_operation=score,
        scorer=scorer,
        telemetry=telemetry,
    )
    instrument_fastapi(app, telemetry.tracing)
    return app


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
