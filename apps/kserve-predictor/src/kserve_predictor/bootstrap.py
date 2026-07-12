"""Composition root for the KServe predictor process."""

from functools import partial

from aiqa_core.adapters.config import load_feature_contract
from aiqa_observability import create_telemetry, load_telemetry_policy
from aiqa_observability.adapters import instrument_fastapi
from aiqa_serving.adapters import LocalSklearnRiskScorer, sha256_file
from aiqa_serving.application import score_risk
from fastapi import FastAPI

from kserve_predictor.adapters import build_http_app
from kserve_predictor.settings import KServePredictorSettings


def build_application(settings: KServePredictorSettings) -> FastAPI:
    """Assemble the KServe V2 adapter around a bound scoring operation."""
    feature_set = load_feature_contract(settings.feature_contract_path)
    scorer = LocalSklearnRiskScorer(
        settings.model_bundle_path,
        sha256_file(settings.feature_contract_path),
        expected_model_sha256=settings.expected_model_sha256,
    )
    telemetry = create_telemetry(
        service_name="kserve-risk-predictor",
        environment=settings.environment,
        policy=load_telemetry_policy(settings.telemetry_config_path),
        otlp_endpoint=str(settings.otlp_endpoint) if settings.otlp_endpoint else None,
    )

    app = build_http_app(
        model_name=settings.model_name,
        score_operation=partial(
            score_risk,
            feature_set=feature_set,
            scorer=scorer,
        ),
        scorer=scorer,
        telemetry=telemetry,
    )
    instrument_fastapi(app, telemetry.tracing)
    return app
