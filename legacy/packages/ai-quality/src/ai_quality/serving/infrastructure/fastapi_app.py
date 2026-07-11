"""FastAPI application for the chapter 3 serving lab."""

from __future__ import annotations

from uuid import uuid4

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

from ai_quality.common.config import load_yaml
from ai_quality.common.paths import config_path
from ai_quality.serving.application.predict_risk import PredictRisk
from ai_quality.serving.domain.model_metadata import ModelMetadata
from ai_quality.serving.domain.prediction_request import PredictionRequest
from ai_quality.serving.infrastructure.json_prediction_event_sink import (
    JsonPredictionEventSink,
)
from ai_quality.serving.infrastructure.runtime_settings import (
    RuntimeSettings,
    read_runtime_settings,
)
from ai_quality.serving.infrastructure.sklearn_model_loader import (
    load_sklearn_scoring_model,
)


# docs:start PredictionRequest
class PredictionPayload(BaseModel):
    """FastAPI request schema for one prediction."""

    request_id: str | None = Field(default=None)
    heart_rate: float
    respiratory_rate: float
    body_temperature: float
    oxygen_saturation: float
    systolic_blood_pressure: float
    diastolic_blood_pressure: float
# docs:end PredictionRequest


# docs:start PredictionResponse
class PredictionOutput(BaseModel):
    """FastAPI response schema for one prediction."""

    request_id: str
    model_version: str
    score: float
    threshold: float
    prediction: str
# docs:end PredictionResponse


def load_model_metadata() -> ModelMetadata:
    """Load model metadata for serving."""
    return ModelMetadata.from_config(
        load_yaml(config_path("validation", "model_metadata.yaml"))
    )


# docs:start create_app
def create_app(
    settings: RuntimeSettings | None = None,
    metadata: ModelMetadata | None = None,
) -> FastAPI:
    """Create the FastAPI app with configured model and threshold."""
    runtime_settings = settings or read_runtime_settings()
    model_metadata = metadata or load_model_metadata()
    scoring_model = load_sklearn_scoring_model(
        model_path=runtime_settings.model_path,
        feature_columns=model_metadata.feature_columns,
    )
    use_case = PredictRisk(
        model=scoring_model,
        threshold=runtime_settings.threshold,
        model_version=runtime_settings.model_version,
        event_sink=JsonPredictionEventSink(runtime_settings.event_log_path),
    )

    app = FastAPI(title="AI Quality Serving Demo")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "model_version": runtime_settings.model_version,
        }

    @app.post("/predict", response_model=PredictionOutput)
    def predict(payload: PredictionPayload) -> dict[str, str | float]:
        request_id = payload.request_id or str(uuid4())
        request = PredictionRequest.from_mapping(
            request_id=request_id,
            payload=payload.model_dump(exclude={"request_id"}),
            feature_columns=list(model_metadata.feature_columns),
        )
        return use_case.run(request).to_dict()

    return app
# docs:end create_app


def main() -> None:
    """Run the API server."""
    settings = read_runtime_settings()
    uvicorn.run(
        "ai_quality.serving.infrastructure.fastapi_app:create_app",
        host=settings.host,
        port=settings.port,
        factory=True,
    )


if __name__ == "__main__":
    main()
