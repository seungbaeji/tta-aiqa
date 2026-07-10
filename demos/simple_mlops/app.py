"""FastAPI serving app for the simple MLOps demo.

이 파일은 "학습된 최신 모델을 API로 제공하고, 예측 이벤트를 남기는" 역할만 합니다.
모델 학습은 train.py, 운영 트래픽 흉내는 send_fake_traffic.py가 담당합니다.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# 학습 코드와 serving 코드가 반드시 같은 feature 순서를 사용해야 합니다.
FEATURES = [
    "heart_rate",
    "respiratory_rate",
    "body_temperature",
    "oxygen_saturation",
    "systolic_blood_pressure",
    "diastolic_blood_pressure",
]

# Docker에서는 /app/... 경로를 쓰고, 로컬 실행에서는 환경 변수로 바꿀 수 있습니다.
MODEL_PATH = Path(os.getenv("MODEL_PATH", "/app/models/latest_model.joblib"))
METADATA_PATH = Path(os.getenv("METADATA_PATH", "/app/models/latest_metadata.json"))
EVENTS_PATH = Path(os.getenv("EVENTS_PATH", "/app/events/predictions.jsonl"))

app = FastAPI(title="Simple AIQA Risk API", version="0.1.0")

# 요청마다 모델 파일을 다시 읽으면 느리므로 메모리에 cache합니다.
# 대신 파일 수정 시간이 바뀌면 새 모델로 자동 reload합니다.
model_bundle: dict[str, Any] | None = None
model_mtime: float | None = None


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


def load_model_if_needed(force: bool = False) -> dict[str, Any]:
    """Load the latest model only when needed.

    trainer-loop가 새 모델 파일을 덮어쓰면, 다음 요청에서 수정 시간을 보고 reload합니다.
    작은 데모에서는 이 방식으로 "재배포 없는 최신 모델 반영" 흐름을 보여줍니다.
    """

    global model_bundle, model_mtime

    if not MODEL_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"Model file not found: {MODEL_PATH}. "
                "Run: docker compose --profile train run --rm trainer"
            ),
        )

    current_mtime = MODEL_PATH.stat().st_mtime
    if force or model_bundle is None or model_mtime != current_mtime:
        model_bundle = joblib.load(MODEL_PATH)
        model_mtime = current_mtime
    return model_bundle


def append_event(event: dict[str, Any]) -> None:
    """Append one prediction event as JSONL.

    운영에서는 이런 이벤트가 로그/모니터링/드리프트 분석의 기본 재료가 됩니다.
    """

    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")


def predict_one(payload: PredictionRequest) -> dict[str, Any]:
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

    # 예측 결과와 모델 정보를 함께 남겨야
    # 나중에 "어떤 모델이 판단했나"를 추적할 수 있습니다.
    event = {
        "event_time": datetime.now(UTC).isoformat(),
        "request_id": payload.request_id or str(uuid4()),
        "features": row,
        "risk_probability": probability,
        "predicted_label": label,
        "model_run_id": metadata.get("run_id"),
        "model_trained_at": metadata.get("trained_at"),
    }
    append_event(event)
    return event


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "simple-aiqa-risk-api", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health() -> dict[str, Any]:
    # health endpoint는 API process뿐 아니라 모델 파일 준비 여부까지 확인합니다.
    metadata: dict[str, Any] = {}
    if METADATA_PATH.exists():
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    if not MODEL_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail={
                "ok": False,
                "model_exists": False,
                "model_path": str(MODEL_PATH),
                "hint": "wait for trainer-loop or run trainer once",
            },
        )
    return {
        "ok": True,
        "model_exists": MODEL_PATH.exists(),
        "model_path": str(MODEL_PATH),
        "events_path": str(EVENTS_PATH),
        "model_run_id": metadata.get("run_id"),
        "model_trained_at": metadata.get("trained_at"),
    }


@app.post("/reload")
def reload_model() -> dict[str, Any]:
    # 수동으로 최신 모델을 다시 읽고 싶을 때 사용하는 운영용 endpoint입니다.
    bundle = load_model_if_needed(force=True)
    return {"reloaded": True, "metadata": bundle.get("metadata", {})}


@app.post("/predict")
def predict(payload: PredictionRequest) -> dict[str, Any]:
    return predict_one(payload)


@app.post("/predict-batch")
def predict_batch(payloads: list[PredictionRequest]) -> dict[str, Any]:
    # batch도 내부적으로는 단건 예측을 반복해서 같은 event format을 유지합니다.
    return {"items": [predict_one(payload) for payload in payloads]}


@app.get("/events")
def events(limit: int = 20) -> dict[str, Any]:
    # 데모 확인용 endpoint입니다.
    # 실제 운영에서는 로그 저장소나 observability 도구를 조회합니다.
    if not EVENTS_PATH.exists():
        return {"items": []}
    lines = EVENTS_PATH.read_text(encoding="utf-8").splitlines()
    items = [json.loads(line) for line in lines[-limit:]]
    return {"items": items}
