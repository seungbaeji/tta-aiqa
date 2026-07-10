"""FastAPI serving app for the simple MLOps demo.

이 파일은 "학습된 최신 모델을 API로 제공하고, 예측 이벤트를 남기는" 역할만 합니다.
모델 학습은 train.py, 운영 트래픽 흉내는 send_fake_traffic.py가 담당합니다.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from config import load_settings

# 학습 코드와 serving 코드가 반드시 같은 feature 순서를 사용해야 합니다.
FEATURES = [
    "heart_rate",
    "respiratory_rate",
    "body_temperature",
    "oxygen_saturation",
    "systolic_blood_pressure",
    "diastolic_blood_pressure",
]

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


class ObservabilityState:
    """Keep lightweight runtime signals for Prometheus and trace correlation."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._events: list[dict[str, Any]] = []
        self._baseline = load_baseline_distribution(SETTINGS.baseline_data_path)

    def record(self, event: dict[str, Any]) -> None:
        with self._lock:
            self._events.append(event)

    def render_prometheus(self) -> str:
        with self._lock:
            events = list(self._events)
            baseline = self._baseline

        request_total = len(events)
        error_total = sum(1 for event in events if int(event["status_code"]) >= 400)
        validation_failure_total = sum(
            1 for event in events if bool(event["validation_failure"])
        )
        valid_events = [event for event in events if not event["validation_failure"]]
        scored_events = [
            event for event in events if isinstance(event.get("score"), int | float)
        ]
        valid_scored_events = [
            event
            for event in valid_events
            if isinstance(event.get("score"), int | float)
        ]

        lines = [
            "# TYPE ai_quality_request_total counter",
            f"ai_quality_request_total {request_total}",
            "# TYPE ai_quality_error_total counter",
            f"ai_quality_error_total {error_total}",
            "# TYPE ai_quality_validation_failure_total counter",
            f"ai_quality_validation_failure_total {validation_failure_total}",
            "# TYPE ai_quality_latency_average_ms gauge",
            f"ai_quality_latency_average_ms {average(events, 'latency_ms'):.3f}",
            "# TYPE ai_quality_score_average gauge",
            f"ai_quality_score_average {average(scored_events, 'score'):.6f}",
            "# TYPE ai_quality_high_risk_rate gauge",
            f"ai_quality_high_risk_rate {prediction_rate(scored_events):.6f}",
            "# TYPE ai_quality_valid_request_total counter",
            f"ai_quality_valid_request_total {len(valid_events)}",
            "# TYPE ai_quality_valid_score_average gauge",
            f"ai_quality_valid_score_average "
            f"{average(valid_scored_events, 'score'):.6f}",
            "# TYPE ai_quality_valid_high_risk_rate gauge",
            f"ai_quality_valid_high_risk_rate "
            f"{prediction_rate(valid_scored_events):.6f}",
            "# TYPE ai_quality_prediction_count gauge",
        ]
        for scope, scoped_events in (
            ("all", scored_events),
            ("valid", valid_scored_events),
        ):
            for prediction in ("high_risk", "low_risk"):
                count = sum(
                    1
                    for event in scoped_events
                    if event.get("prediction") == prediction
                )
                lines.append(
                    "ai_quality_prediction_count"
                    f'{{prediction="{prediction}",scope="{scope}"}} {count}'
                )

        lines.append("# TYPE ai_quality_score_bucket_count gauge")
        for scope, scoped_events in (
            ("all", scored_events),
            ("valid", valid_scored_events),
        ):
            for bucket in bucket_labels(SETTINGS.score_buckets):
                count = sum(
                    1
                    for event in scoped_events
                    if bucket_for(float(event["score"]), SETTINGS.score_buckets)
                    == bucket
                )
                lines.append(
                    "ai_quality_score_bucket_count"
                    f'{{bucket="{bucket}",scope="{scope}"}} {count}'
                )

        lines.extend(render_input_distribution_metrics(events, baseline))
        return "\n".join(lines) + "\n"


def average(events: list[dict[str, Any]], key: str) -> float:
    values = [float(event[key]) for event in events if event.get(key) is not None]
    if not values:
        return 0.0
    return sum(values) / len(values)


def prediction_rate(events: list[dict[str, Any]]) -> float:
    if not events:
        return 0.0
    high_risk_count = sum(
        1 for event in events if event.get("prediction") == "high_risk"
    )
    return high_risk_count / len(events)


def bucket_labels(edges: tuple[float, ...]) -> list[str]:
    return [
        f"{edges[index]:.1f}-{edges[index + 1]:.1f}"
        for index in range(len(edges) - 1)
    ]


def bucket_for(value: float, edges: tuple[float, ...]) -> str:
    labels = bucket_labels(edges)
    for index, label in enumerate(labels):
        lower = edges[index]
        upper = edges[index + 1]
        if lower <= value < upper or (index == len(labels) - 1 and value <= upper):
            return label
    if value < edges[0]:
        return labels[0]
    return labels[-1]


def load_baseline_distribution(path: Path) -> dict[str, dict[str, Any]]:
    """Load baseline feature statistics used by the dashboard drift panels."""

    if not path.exists():
        return {}

    dataframe = pd.read_csv(path)
    baseline: dict[str, dict[str, Any]] = {}
    for feature in SETTINGS.input_distribution_features:
        if feature not in dataframe.columns:
            continue
        values = [float(value) for value in dataframe[feature].dropna().tolist()]
        if not values:
            continue
        edges = histogram_edges(values)
        baseline[feature] = {
            "mean": sum(values) / len(values),
            "edges": edges,
            "counts": histogram_counts(values, edges),
        }
    return baseline


def histogram_edges(values: list[float], bin_count: int = 5) -> tuple[float, ...]:
    lower = min(values)
    upper = max(values)
    if lower == upper:
        upper = lower + 1.0
    width = (upper - lower) / bin_count
    return tuple(lower + width * index for index in range(bin_count + 1))


def histogram_labels(edges: tuple[float, ...]) -> list[str]:
    return [
        f"{edges[index]:.2f}~{edges[index + 1]:.2f}"
        for index in range(len(edges) - 1)
    ]


def histogram_counts(values: list[float], edges: tuple[float, ...]) -> list[int]:
    counts = [0 for _ in range(len(edges) - 1)]
    for value in values:
        for index in range(len(counts)):
            lower = edges[index]
            upper = edges[index + 1]
            if lower <= value < upper or (index == len(counts) - 1 and value <= upper):
                counts[index] += 1
                break
    return counts


def render_input_distribution_metrics(
    events: list[dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
) -> list[str]:
    lines = ["# TYPE ai_quality_input_mean_delta gauge"]
    current_values = {
        feature: [
            float(event["features"][feature])
            for event in events
            if not event["validation_failure"] and feature in event.get("features", {})
        ]
        for feature in SETTINGS.input_distribution_features
    }
    for feature, values in current_values.items():
        baseline_mean = baseline.get(feature, {}).get("mean")
        current_mean = sum(values) / len(values) if values else baseline_mean
        delta = (
            0.0
            if baseline_mean is None or current_mean is None
            else float(current_mean) - float(baseline_mean)
        )
        lines.append(f'ai_quality_input_mean_delta{{feature="{feature}"}} {delta:.6f}')

    lines.append("# TYPE ai_quality_input_histogram_count gauge")
    for feature, baseline_stats in baseline.items():
        edges = baseline_stats["edges"]
        labels = histogram_labels(edges)
        baseline_counts = baseline_stats["counts"]
        current_counts = histogram_counts(current_values.get(feature, []), edges)
        for label, count in zip(labels, baseline_counts, strict=True):
            lines.append(
                "ai_quality_input_histogram_count"
                f'{{feature="{feature}",bucket="{label}",scope="baseline"}} {count}'
            )
        for label, count in zip(labels, current_counts, strict=True):
            lines.append(
                "ai_quality_input_histogram_count"
                f'{{feature="{feature}",bucket="{label}",scope="current"}} {count}'
            )
    return lines


observability = ObservabilityState()


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


def append_event(event: dict[str, Any]) -> None:
    """Append one prediction event as JSONL and emit it as a structured log.

    운영에서는 이런 이벤트가 로그/모니터링/드리프트 분석의 기본 재료가 됩니다.
    """

    SETTINGS.events_path.parent.mkdir(parents=True, exist_ok=True)
    with SETTINGS.events_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(json.dumps(event, ensure_ascii=False), flush=True)


def _hex_digest(value: str, length: int) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:length]


def tempo_trace_id(course_trace_id: str) -> str:
    return _hex_digest(course_trace_id, 32)


def span_id(value: str) -> str:
    return _hex_digest(value, 16)


def otlp_attribute(key: str, value: str | int | float | bool | None) -> dict[str, Any]:
    if isinstance(value, bool):
        encoded: dict[str, Any] = {"boolValue": value}
    elif isinstance(value, int):
        encoded = {"intValue": str(value)}
    elif isinstance(value, float):
        encoded = {"doubleValue": value}
    else:
        encoded = {"stringValue": "" if value is None else str(value)}
    return {"key": key, "value": encoded}


def otlp_span(
    *,
    trace_id: str,
    span_id_value: str,
    parent_span_id: str | None,
    name: str,
    kind: int,
    start_ns: int,
    duration_ms: float,
    attributes: list[dict[str, Any]],
) -> dict[str, Any]:
    span: dict[str, Any] = {
        "traceId": trace_id,
        "spanId": span_id_value,
        "name": name,
        "kind": kind,
        "startTimeUnixNano": str(start_ns),
        "endTimeUnixNano": str(start_ns + int(max(duration_ms, 0.1) * 1_000_000)),
        "attributes": attributes,
    }
    if parent_span_id:
        span["parentSpanId"] = parent_span_id
    return span


def send_trace(event: dict[str, Any], start_ns: int) -> None:
    """Send one request trace to the configured OTLP/HTTP endpoint."""

    if not SETTINGS.otlp_traces_endpoint:
        return

    course_trace_id = str(event["trace_id"])
    trace_id = tempo_trace_id(course_trace_id)
    root_span_id = span_id(f"{course_trace_id}:server:predict")
    common_attributes = [
        otlp_attribute("deployment.environment", SETTINGS.deployment_environment),
        otlp_attribute("request_id", event["request_id"]),
        otlp_attribute("course_trace_id", course_trace_id),
        otlp_attribute("trace_id", course_trace_id),
        otlp_attribute("model_version", event.get("model_version")),
        otlp_attribute("threshold", event.get("threshold")),
        otlp_attribute("prediction", event.get("prediction")),
        otlp_attribute("validation_failure", event["validation_failure"]),
    ]
    spans = [
        otlp_span(
            trace_id=trace_id,
            span_id_value=root_span_id,
            parent_span_id=None,
            name="POST /predict",
            kind=2,
            start_ns=start_ns,
            duration_ms=float(event["latency_ms"]),
            attributes=[
                *common_attributes,
                otlp_attribute("http.method", "POST"),
                otlp_attribute("http.status_code", event["status_code"]),
                otlp_attribute("score", event.get("score")),
            ],
        )
    ]
    child_specs = (
        ("validate_payload", 0.0, 8.0),
        ("score_model", 8.0, max(3.0, float(event["latency_ms"]) - 16.0)),
        ("emit_observability", max(12.0, float(event["latency_ms"]) - 8.0), 8.0),
    )
    for name, offset_ms, duration_ms in child_specs:
        spans.append(
            otlp_span(
                trace_id=trace_id,
                span_id_value=span_id(f"{course_trace_id}:server:{name}"),
                parent_span_id=root_span_id,
                name=name,
                kind=1,
                start_ns=start_ns + int(offset_ms * 1_000_000),
                duration_ms=duration_ms,
                attributes=common_attributes,
            )
        )

    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        otlp_attribute("service.name", SETTINGS.service_name),
                        otlp_attribute(
                            "deployment.environment",
                            SETTINGS.deployment_environment,
                        ),
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {
                            "name": "simple-aiqa-mlops",
                            "version": "0.1.0",
                        },
                        "spans": spans,
                    }
                ],
            }
        ]
    }
    request = urllib.request.Request(
        SETTINGS.otlp_traces_endpoint,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=SETTINGS.otlp_timeout_seconds):
            return
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        print(
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "level": "warning",
                    "event": "otlp_trace_send_failed",
                    "request_id": event["request_id"],
                    "trace_id": event["trace_id"],
                    "error": str(error),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )


def record_observability_event(event: dict[str, Any], start_ns: int) -> None:
    append_event(event)
    observability.record(event)
    send_trace(event, start_ns)


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
        "features": {feature: body.get(feature) for feature in FEATURES},
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
    row = {feature: getattr(payload, feature) for feature in FEATURES}
    frame = pd.DataFrame([row], columns=FEATURES)

    # binary classifier의 positive class(high_risk) 확률을 사용합니다.
    probability = float(model.predict_proba(frame)[0, 1])
    threshold = float(metadata.get("threshold", 0.5))
    label = "high_risk" if probability >= threshold else "low_risk"
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
