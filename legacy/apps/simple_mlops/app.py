"""FastAPI serving app for the simple MLOps demo.

이 파일은 "학습된 최신 모델을 API로 제공하고, 예측 이벤트를 남기는" 역할만 합니다.
모델 학습은 train.py, 운영 트래픽 흉내는 send_fake_traffic.py가 담당합니다.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import joblib
import pandas as pd
from aiqa_core.contracts import (
    DEFAULT_THRESHOLD,
    FEATURE_COLUMNS,
    NEGATIVE_LABEL,
    POSITIVE_LABEL,
)
from aiqa_observability import (
    ObservabilityState,
    TraceSettings,
    append_prediction_event,
    send_trace,
)
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from config import load_settings

SETTINGS = load_settings()

app = FastAPI(title="Simple AIQA Risk API", version="0.1.0")

# 요청마다 모델 파일을 다시 읽으면 느리므로 메모리에 cache합니다.
# 대신 파일 수정 시간이 바뀌면 새 모델로 자동 reload합니다.
model_bundle: dict[str, Any] | None = None
model_mtime: float | None = None
observability = None


class PredictionRequest(BaseModel):
    """API 입력 schema.

    Field의 ge/le 범위는 잘못된 운영 입력을 API 입구에서 막는 간단한 계약입니다.
    """

    heart_rate: float = Field(..., ge=20, le=240)
    respiratory_rate: float = Field(..., ge=4, le=80)
    body_temperature: float = Field(..., ge=30, le=45)
    oxygen_saturation: float = Field(..., ge=50, le=100)
    systolic_blood_pressure: float = Field(..., ge=50, le=260)
    diastolic_blood_pressure: float = Field(..., ge=30, le=180)
    request_id: str | None = None
    trace_id: str | None = None


observability = ObservabilityState(
    SETTINGS.baseline_data_path,
    SETTINGS.input_distribution_features,
    SETTINGS.score_buckets,
)


def load_model_if_needed(force: bool = False) -> dict[str, Any]:
    """Load the latest model only when needed.

    trainer-loop가 새 모델 파일을 덮어쓰면, 다음 요청에서 수정 시간을 보고 reload합니다.
    작은 데모에서는 이 방식으로 "재배포 없는 최신 모델 반영" 흐름을 보여줍니다.
    """

    global model_bundle, model_mtime

    if not SETTINGS.model_path.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"Model file not found: {SETTINGS.model_path}. "
                "Run: docker compose --profile train run --rm trainer"
            ),
        )

    current_mtime = SETTINGS.model_path.stat().st_mtime
    if force or model_bundle is None or model_mtime != current_mtime:
        model_bundle = joblib.load(SETTINGS.model_path)
        model_mtime = current_mtime
    return model_bundle


def record_observability_event(event: dict[str, Any], start_ns: int) -> None:
    append_prediction_event(event, SETTINGS.events_path)
    observability.record(event)
    send_trace(
        event,
        start_ns,
        TraceSettings(
            endpoint=SETTINGS.otlp_traces_endpoint,
            timeout_seconds=SETTINGS.otlp_timeout_seconds,
            service_name=SETTINGS.service_name,
            deployment_environment=SETTINGS.deployment_environment,
        ),
    )


def extract_failed_field(errors: list[dict[str, Any]]) -> str | None:
    if not errors:
        return None
    location = errors[0].get("loc", [])
    if isinstance(location, list | tuple) and location:
        return str(location[-1])
    return None


async def read_request_json(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


@app.middleware("http")
async def attach_correlation_ids(request: Request, call_next: Any) -> Any:
    request.state.started_at = time.perf_counter()
    request.state.start_ns = time.time_ns()
    request.state.request_id = request.headers.get("x-request-id") or str(uuid4())
    request.state.trace_id = (
        request.headers.get("x-trace-id")
        or f"{SETTINGS.trace_id_prefix}-{request.state.request_id}"
    )
    response = await call_next(request)
    response.headers["x-request-id"] = request.state.request_id
    response.headers["x-trace-id"] = request.state.trace_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    body = await read_request_json(request)
    request_id = str(body.get("request_id") or request.state.request_id)
    trace_id = str(body.get("trace_id") or request.state.trace_id)
    latency_ms = (time.perf_counter() - request.state.started_at) * 1000
    failed_field = extract_failed_field(exc.errors())
    timestamp = datetime.now(UTC).isoformat()
    event = {
        "timestamp": timestamp,
        "event_time": timestamp,
        "event": "prediction_validation_failed",
        "service": SETTINGS.service_name,
        "environment": SETTINGS.deployment_environment,
        "request_id": request_id,
        "trace_id": trace_id,
        "features": {feature: body.get(feature) for feature in FEATURE_COLUMNS},
        "score": None,
        "risk_probability": None,
        "threshold": None,
        "prediction": None,
        "predicted_label": None,
        "latency_ms": round(latency_ms, 3),
        "status_code": 422,
        "validation_failure": True,
        "failed_field": failed_field,
        "error_category": "request_validation",
        "error_detail": exc.errors()[0].get("msg") if exc.errors() else "invalid input",
        "client_id": SETTINGS.client_id,
        "source_system": SETTINGS.source_system,
        "model_version": None,
        "model_run_id": None,
        "model_trained_at": None,
    }
    record_observability_event(event, request.state.start_ns)
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "request_id": request_id,
            "trace_id": trace_id,
        },
        headers={"x-request-id": request_id, "x-trace-id": trace_id},
    )


def predict_one(
    payload: PredictionRequest,
    request: Request | None = None,
) -> dict[str, Any]:
    started_at = time.perf_counter()
    start_ns = time.time_ns()
    bundle = load_model_if_needed()
    model = bundle["model"]
    metadata = bundle.get("metadata", {})

    # sklearn model은 DataFrame column 이름과 순서가 학습 때와 같아야 안전합니다.
    row = {feature: getattr(payload, feature) for feature in FEATURE_COLUMNS}
    frame = pd.DataFrame([row], columns=list(FEATURE_COLUMNS))

    # binary classifier의 positive class(high_risk) 확률을 사용합니다.
    probability = float(model.predict_proba(frame)[0, 1])
    threshold = float(metadata.get("threshold", DEFAULT_THRESHOLD))
    label = POSITIVE_LABEL if probability >= threshold else NEGATIVE_LABEL
    request_id = payload.request_id or (
        getattr(request.state, "request_id", None) if request else None
    ) or str(uuid4())
    trace_id = payload.trace_id or (
        getattr(request.state, "trace_id", None) if request else None
    ) or f"{SETTINGS.trace_id_prefix}-{request_id}"
    latency_ms = (time.perf_counter() - started_at) * 1000

    # 예측 결과와 모델 정보를 함께 남겨야
    # 나중에 "어떤 모델이 판단했나"를 추적할 수 있습니다.
    timestamp = datetime.now(UTC).isoformat()
    event = {
        "timestamp": timestamp,
        "event_time": timestamp,
        "event": "prediction",
        "service": SETTINGS.service_name,
        "environment": SETTINGS.deployment_environment,
        "request_id": request_id,
        "trace_id": trace_id,
        "features": row,
        "score": probability,
        "risk_probability": probability,
        "threshold": threshold,
        "prediction": label,
        "predicted_label": label,
        "latency_ms": round(latency_ms, 3),
        "status_code": 200,
        "validation_failure": False,
        "failed_field": None,
        "error_category": None,
        "error_detail": None,
        "client_id": SETTINGS.client_id,
        "source_system": SETTINGS.source_system,
        "model_version": metadata.get("run_id"),
        "model_run_id": metadata.get("run_id"),
        "model_trained_at": metadata.get("trained_at"),
    }
    record_observability_event(event, start_ns)
    return event


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "simple-aiqa-risk-api", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health() -> dict[str, Any]:
    # health endpoint는 API process뿐 아니라 모델 파일 준비 여부까지 확인합니다.
    metadata: dict[str, Any] = {}
    if SETTINGS.metadata_path.exists():
        metadata = json.loads(SETTINGS.metadata_path.read_text(encoding="utf-8"))
    if not SETTINGS.model_path.exists():
        raise HTTPException(
            status_code=503,
            detail={
                "ok": False,
                "model_exists": False,
                "model_path": str(SETTINGS.model_path),
                "hint": "wait for trainer-loop or run trainer once",
            },
        )
    return {
        "ok": True,
        "model_exists": SETTINGS.model_path.exists(),
        "model_path": str(SETTINGS.model_path),
        "metadata_path": str(SETTINGS.metadata_path),
        "events_path": str(SETTINGS.events_path),
        "baseline_data_path": str(SETTINGS.baseline_data_path),
        "metrics_path": "/metrics",
        "service_name": SETTINGS.service_name,
        "deployment_environment": SETTINGS.deployment_environment,
        "otlp_traces_enabled": bool(SETTINGS.otlp_traces_endpoint),
        "model_run_id": metadata.get("run_id"),
        "model_trained_at": metadata.get("trained_at"),
    }


@app.post("/reload")
def reload_model() -> dict[str, Any]:
    # 수동으로 최신 모델을 다시 읽고 싶을 때 사용하는 운영용 endpoint입니다.
    bundle = load_model_if_needed(force=True)
    return {"reloaded": True, "metadata": bundle.get("metadata", {})}


@app.post("/predict")
def predict(payload: PredictionRequest, request: Request) -> dict[str, Any]:
    return predict_one(payload, request)


@app.post("/predict-batch")
def predict_batch(
    payloads: list[PredictionRequest],
    request: Request,
) -> dict[str, Any]:
    # batch도 내부적으로는 단건 예측을 반복해서 같은 event format을 유지합니다.
    return {"items": [predict_one(payload, request) for payload in payloads]}


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(
        observability.render_prometheus(),
        media_type="text/plain; version=0.0.4",
    )


@app.get("/events")
def events(limit: int = 20) -> dict[str, Any]:
    # 데모 확인용 endpoint입니다.
    # 실제 운영에서는 로그 저장소나 observability 도구를 조회합니다.
    if not SETTINGS.events_path.exists():
        return {"items": []}
    lines = SETTINGS.events_path.read_text(encoding="utf-8").splitlines()
    items = [json.loads(line) for line in lines[-limit:]]
    return {"items": items}
