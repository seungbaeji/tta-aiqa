"""Browser-safe helpers for JupyterLite course notebooks.

This module intentionally avoids server runtimes, sklearn models, FastAPI,
MLflow, and filesystem writes. It supports the Lite notebooks as an
inspectable evidence path, while local labs keep using the full package.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

POSITIVE_LABEL = "high_risk"
NEGATIVE_LABEL = "low_risk"
THRESHOLD = 0.50
FEATURE_COLUMNS = [
    "heart_rate",
    "respiratory_rate",
    "body_temperature",
    "oxygen_saturation",
    "systolic_blood_pressure",
    "diastolic_blood_pressure",
]
REQUIRED_COLUMNS = ["patient_id", *FEATURE_COLUMNS, "timestamp", "label"]
VALID_RANGES = {
    "heart_rate": (1, 250),
    "respiratory_rate": (1, 80),
    "body_temperature": (30, 45),
    "oxygen_saturation": (0, 100),
    "systolic_blood_pressure": (50, 250),
    "diastolic_blood_pressure": (30, 150),
    "age": (0, 120),
    "weight_kg": (1, 300),
    "height_m": (0.5, 2.5),
}


def normalize_label(label: object) -> str:
    value = str(label).strip().lower()
    if value in {"high_risk", "high risk", "positive", "1"}:
        return POSITIVE_LABEL
    if value in {"low_risk", "low risk", "negative", "0"}:
        return NEGATIVE_LABEL
    return value


def sample_vital_signs() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "patient_id": "p-001",
                "timestamp": "2026-01-01T09:00:00Z",
                "heart_rate": 72,
                "respiratory_rate": 16,
                "body_temperature": 36.6,
                "oxygen_saturation": 98,
                "systolic_blood_pressure": 118,
                "diastolic_blood_pressure": 76,
                "age": 38,
                "label": "low_risk",
            },
            {
                "patient_id": "p-002",
                "timestamp": "2026-01-01T09:01:00Z",
                "heart_rate": 118,
                "respiratory_rate": 25,
                "body_temperature": 37.9,
                "oxygen_saturation": 92,
                "systolic_blood_pressure": 146,
                "diastolic_blood_pressure": 92,
                "age": 65,
                "label": "high_risk",
            },
            {
                "patient_id": "p-003",
                "timestamp": "2026-01-01T09:02:00Z",
                "heart_rate": 63,
                "respiratory_rate": 15,
                "body_temperature": 36.4,
                "oxygen_saturation": 99,
                "systolic_blood_pressure": 110,
                "diastolic_blood_pressure": 70,
                "age": 29,
                "label": "low_risk",
            },
            {
                "patient_id": "p-004",
                "timestamp": "2026-01-01T09:03:00Z",
                "heart_rate": 132,
                "respiratory_rate": 28,
                "body_temperature": 38.4,
                "oxygen_saturation": 89,
                "systolic_blood_pressure": 158,
                "diastolic_blood_pressure": 96,
                "age": 72,
                "label": "high_risk",
            },
            {
                "patient_id": "p-005",
                "timestamp": "2026-01-01T09:04:00Z",
                "heart_rate": 84,
                "respiratory_rate": 18,
                "body_temperature": 36.8,
                "oxygen_saturation": 97,
                "systolic_blood_pressure": 126,
                "diastolic_blood_pressure": 78,
                "age": 41,
                "label": "low_risk",
            },
            {
                "patient_id": "p-006",
                "timestamp": "2026-01-01T09:05:00Z",
                "heart_rate": None,
                "respiratory_rate": 22,
                "body_temperature": 37.2,
                "oxygen_saturation": 93,
                "systolic_blood_pressure": 138,
                "diastolic_blood_pressure": 88,
                "age": 58,
                "label": "high_risk",
            },
            {
                "patient_id": "p-007",
                "timestamp": "2026-01-01T09:06:00Z",
                "heart_rate": 78,
                "respiratory_rate": 17,
                "body_temperature": 36.5,
                "oxygen_saturation": 101,
                "systolic_blood_pressure": 122,
                "diastolic_blood_pressure": 75,
                "age": 44,
                "label": "low_risk",
            },
            {
                "patient_id": "p-008",
                "timestamp": "2026-01-01T09:07:00Z",
                "heart_rate": 125,
                "respiratory_rate": 27,
                "body_temperature": 38.2,
                "oxygen_saturation": 90,
                "systolic_blood_pressure": 152,
                "diastolic_blood_pressure": 94,
                "age": 69,
                "label": "high_risk",
            },
            {
                "patient_id": "p-009",
                "timestamp": "2026-01-01T09:08:00Z",
                "heart_rate": 68,
                "respiratory_rate": 14,
                "body_temperature": 36.2,
                "oxygen_saturation": 99,
                "systolic_blood_pressure": 114,
                "diastolic_blood_pressure": 72,
                "age": 31,
                "label": "low_risk",
            },
            {
                "patient_id": "p-010",
                "timestamp": "2026-01-01T09:09:00Z",
                "heart_rate": 141,
                "respiratory_rate": 31,
                "body_temperature": 38.8,
                "oxygen_saturation": 86,
                "systolic_blood_pressure": 164,
                "diastolic_blood_pressure": 102,
                "age": 77,
                "label": "high_risk",
            },
            {
                "patient_id": "p-011",
                "timestamp": "2026-01-01T09:10:00Z",
                "heart_rate": 88,
                "respiratory_rate": 19,
                "body_temperature": 37.0,
                "oxygen_saturation": 95,
                "systolic_blood_pressure": 130,
                "diastolic_blood_pressure": 82,
                "age": 49,
                "label": "low_risk",
            },
            {
                "patient_id": "p-012",
                "timestamp": "2026-01-01T09:11:00Z",
                "heart_rate": 119,
                "respiratory_rate": 26,
                "body_temperature": 37.7,
                "oxygen_saturation": 91,
                "systolic_blood_pressure": 148,
                "diastolic_blood_pressure": 91,
                "age": 63,
                "label": "high_risk",
            },
        ]
    )


def load_csv_or_sample(
    path: str, sample: pd.DataFrame, nrows: int | None = 2000
) -> tuple[pd.DataFrame, str]:
    candidates = [Path(path), Path("..") / path, Path("../..") / path]
    for candidate in candidates:
        if candidate.exists():
            return pd.read_csv(candidate, nrows=nrows), f"loaded {candidate}"
    return sample.copy(), "embedded JupyterLite sample"


def score_rows(dataframe: pd.DataFrame) -> list[float]:
    scores: list[float] = []
    for _, row in dataframe.iterrows():
        score = 0.08
        score += max(float(row.get("heart_rate", 80) or 80) - 80, 0) / 120 * 0.28
        score += max(float(row.get("respiratory_rate", 16) or 16) - 16, 0) / 30 * 0.18
        score += max(96 - float(row.get("oxygen_saturation", 96) or 96), 0) / 16 * 0.30
        score += (
            max(float(row.get("body_temperature", 36.5) or 36.5) - 37.0, 0) / 4 * 0.12
        )
        score += (
            max(float(row.get("systolic_blood_pressure", 120) or 120) - 130, 0)
            / 70
            * 0.12
        )
        scores.append(round(min(max(score, 0.01), 0.99), 4))
    return scores


@dataclass(frozen=True)
class Confusion:
    true_positive: int
    true_negative: int
    false_positive: int
    false_negative: int

    @property
    def accuracy(self) -> float:
        total = (
            self.true_positive
            + self.true_negative
            + self.false_positive
            + self.false_negative
        )
        return (self.true_positive + self.true_negative) / total if total else 0.0

    @property
    def precision(self) -> float:
        denominator = self.true_positive + self.false_positive
        return self.true_positive / denominator if denominator else 0.0

    @property
    def recall(self) -> float:
        denominator = self.true_positive + self.false_negative
        return self.true_positive / denominator if denominator else 0.0

    @property
    def f1(self) -> float:
        denominator = self.precision + self.recall
        return 2 * self.precision * self.recall / denominator if denominator else 0.0


def confusion_from_scores(
    labels: list[object], scores: list[float], threshold: float = THRESHOLD
) -> Confusion:
    tp = tn = fp = fn = 0
    for label, score in zip(labels, scores, strict=False):
        truth = normalize_label(label)
        prediction = POSITIVE_LABEL if float(score) >= threshold else NEGATIVE_LABEL
        if truth == POSITIVE_LABEL and prediction == POSITIVE_LABEL:
            tp += 1
        elif truth == NEGATIVE_LABEL and prediction == NEGATIVE_LABEL:
            tn += 1
        elif truth == NEGATIVE_LABEL and prediction == POSITIVE_LABEL:
            fp += 1
        elif truth == POSITIVE_LABEL and prediction == NEGATIVE_LABEL:
            fn += 1
    return Confusion(tp, tn, fp, fn)


def metric_row(
    dataset_name: str,
    labels: list[object],
    scores: list[float],
    threshold: float = THRESHOLD,
) -> dict[str, object]:
    matrix = confusion_from_scores(labels, scores, threshold)
    return {
        "dataset": dataset_name,
        "threshold": threshold,
        "row_count": len(labels),
        "accuracy": round(matrix.accuracy, 4),
        "precision": round(matrix.precision, 4),
        "recall": round(matrix.recall, 4),
        "f1": round(matrix.f1, 4),
        "TP": matrix.true_positive,
        "TN": matrix.true_negative,
        "FP": matrix.false_positive,
        "FN": matrix.false_negative,
    }


def threshold_table(
    labels: list[object], scores: list[float], thresholds: list[float]
) -> pd.DataFrame:
    rows = []
    for threshold in thresholds:
        row = metric_row("threshold_check", labels, scores, threshold)
        rows.append(
            {
                "threshold": threshold,
                "precision": row["precision"],
                "recall": row["recall"],
                "false_positive": row["FP"],
                "false_negative": row["FN"],
            }
        )
    return pd.DataFrame(rows)


class LiteResponse:
    """Small response object used by the browser-only serving notebook."""

    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload


def serving_payload() -> dict[str, object]:
    return {
        "request_id": "lab-03-valid-001",
        "heart_rate": 118,
        "respiratory_rate": 25,
        "body_temperature": 37.9,
        "oxygen_saturation": 92,
        "systolic_blood_pressure": 146,
        "diastolic_blood_pressure": 92,
    }


def validate_payload(payload: dict[str, object]) -> list[dict[str, object]]:
    errors: list[dict[str, object]] = []
    for field in FEATURE_COLUMNS:
        if field not in payload:
            errors.append(
                {"loc": ["body", field], "msg": "Field required", "type": "missing"}
            )
            continue
        try:
            float(payload[field])
        except (TypeError, ValueError):
            errors.append(
                {
                    "loc": ["body", field],
                    "msg": "Input should be a valid number",
                    "type": "float_parsing",
                }
            )
    return errors


def post_predict(payload: dict[str, object]) -> LiteResponse:
    errors = validate_payload(payload)
    if errors:
        return LiteResponse(422, {"detail": errors})
    dataframe = pd.DataFrame([payload])
    score = score_rows(dataframe)[0]
    return LiteResponse(
        200,
        {
            "request_id": str(payload.get("request_id", "generated-request-id")),
            "model_version": "v1",
            "score": score,
            "threshold": THRESHOLD,
            "prediction": POSITIVE_LABEL if score >= THRESHOLD else NEGATIVE_LABEL,
        },
    )


def openapi_contract() -> dict[str, object]:
    properties = {field: {"type": "number"} for field in FEATURE_COLUMNS}
    properties["request_id"] = {"type": "string"}
    return {
        "components": {
            "schemas": {
                "PredictionPayload": {
                    "type": "object",
                    "required": FEATURE_COLUMNS,
                    "properties": properties,
                },
                "PredictionOutput": {
                    "type": "object",
                    "required": [
                        "request_id",
                        "model_version",
                        "score",
                        "threshold",
                        "prediction",
                    ],
                },
                "HTTPValidationError": {
                    "type": "object",
                    "properties": {"detail": {"type": "array"}},
                },
            }
        },
        "paths": {
            "/predict": {
                "post": {
                    "requestBody": "PredictionPayload",
                    "responses": {
                        "200": "PredictionOutput",
                        "422": "HTTPValidationError",
                    },
                }
            }
        },
    }


def generate_events(scenario: str, count: int = 30) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for index in range(count):
        score = (
            min(0.99, 0.45 + (index % 10) * 0.055)
            if scenario == "anomaly"
            else 0.25 + (index % 10) * 0.05
        )
        status_code = 422 if scenario == "anomaly" and index % 9 == 0 else 200
        validation_failure = status_code >= 400
        events.append(
            {
                "timestamp": f"2026-01-01T09:{index:02d}:00Z",
                "request_id": f"{scenario}-{index:04d}",
                "trace_id": f"{scenario}-trace-{index // 3:04d}",
                "model_version": "v1",
                "score": round(score, 4),
                "threshold": 0.5,
                "prediction": "high_risk" if score >= 0.5 else "low_risk",
                "latency_ms": (180.0 if scenario == "anomaly" else 60.0)
                + (index % 8) * 12.5,
                "status_code": status_code,
                "validation_failure": validation_failure,
                "client_id": "partner-feed-v2"
                if validation_failure
                else (
                    "mobile-checkin-v2"
                    if scenario == "anomaly"
                    else "baseline-client-v1"
                ),
                "source_system": "upstream-partner-feed"
                if validation_failure
                else (
                    "mobile-checkin" if scenario == "anomaly" else "training-baseline"
                ),
                "failed_field": (
                    "oxygen_saturation" if index % 2 == 0 else "heart_rate"
                )
                if validation_failure
                else None,
                "owner": "Client Integration" if validation_failure else None,
            }
        )
    return events


def quality_snapshot(events: list[dict[str, object]]) -> dict[str, float | int]:
    request_count = len(events)
    valid_events = [event for event in events if not event["validation_failure"]]
    high_risk_count = sum(1 for event in events if event["prediction"] == "high_risk")
    low_risk_count = sum(1 for event in events if event["prediction"] == "low_risk")
    valid_high_risk_count = sum(
        1 for event in valid_events if event["prediction"] == "high_risk"
    )
    return {
        "request_count": request_count,
        "error_count": sum(1 for event in events if int(event["status_code"]) >= 400),
        "validation_failure_count": sum(
            1 for event in events if event["validation_failure"]
        ),
        "average_latency_ms": round(
            sum(float(event["latency_ms"]) for event in events) / request_count, 3
        ),
        "high_risk_count": high_risk_count,
        "low_risk_count": low_risk_count,
        "high_risk_rate": round(high_risk_count / request_count, 4),
        "average_score": round(
            sum(float(event["score"]) for event in events) / request_count, 4
        ),
        "error_rate": round(
            sum(1 for event in events if int(event["status_code"]) >= 400)
            / request_count,
            4,
        ),
        "valid_request_count": len(valid_events),
        "valid_high_risk_rate": round(valid_high_risk_count / len(valid_events), 4)
        if valid_events
        else 0.0,
    }


def compare_snapshots(
    baseline: dict[str, float | int], current: dict[str, float | int]
) -> dict[str, object]:
    notes: list[str] = []
    error_rate_delta = float(current["error_rate"]) - float(baseline["error_rate"])
    latency_delta_ms = float(current["average_latency_ms"]) - float(
        baseline["average_latency_ms"]
    )
    high_risk_rate_delta = float(current["high_risk_rate"]) - float(
        baseline["high_risk_rate"]
    )
    average_score_delta = float(current["average_score"]) - float(
        baseline["average_score"]
    )
    if error_rate_delta > 0.03:
        notes.append("오류율이 증가했습니다. 검증 실패를 확인합니다.")
    if latency_delta_ms > 100:
        notes.append(
            "지연 시간이 증가했습니다. 서비스 부하나 의존성 지연을 확인합니다."
        )
    if high_risk_rate_delta > 0.15:
        notes.append("예측 분포가 high_risk 쪽으로 이동했습니다.")
    if average_score_delta > 0.10:
        notes.append("점수 분포가 높은 방향으로 이동했습니다.")
    return {
        "error_rate_delta": round(error_rate_delta, 4),
        "latency_delta_ms": round(latency_delta_ms, 3),
        "high_risk_rate_delta": round(high_risk_rate_delta, 4),
        "average_score_delta": round(average_score_delta, 4),
        "notes": notes,
    }


def render_prometheus(snapshot: dict[str, float | int]) -> str:
    return "\n".join(
        [
            "# TYPE ai_quality_request_total counter",
            f"ai_quality_request_total {snapshot['request_count']}",
            "# TYPE ai_quality_error_total counter",
            f"ai_quality_error_total {snapshot['error_count']}",
            "# TYPE ai_quality_validation_failure_total counter",
            (
                "ai_quality_validation_failure_total "
                f"{snapshot['validation_failure_count']}"
            ),
            "# TYPE ai_quality_latency_average_ms gauge",
            f"ai_quality_latency_average_ms {snapshot['average_latency_ms']:.3f}",
            "# TYPE ai_quality_score_average gauge",
            f"ai_quality_score_average {snapshot['average_score']:.6f}",
            "# TYPE ai_quality_high_risk_rate gauge",
            f"ai_quality_high_risk_rate {snapshot['high_risk_rate']:.6f}",
        ]
    )


def compare_input_distribution(
    baseline: pd.DataFrame, current: pd.DataFrame, feature_columns: list[str]
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for feature in feature_columns:
        baseline_values = pd.to_numeric(baseline[feature], errors="coerce").dropna()
        current_values = pd.to_numeric(current[feature], errors="coerce").dropna()
        baseline_mean = float(baseline_values.mean())
        current_mean = float(current_values.mean())
        delta = current_mean - baseline_mean
        ratio = delta / abs(baseline_mean) if baseline_mean else delta
        rows.append(
            {
                "feature": feature,
                "baseline_mean": round(baseline_mean, 4),
                "current_mean": round(current_mean, 4),
                "mean_delta": round(delta, 4),
                "delta_ratio": round(ratio, 4),
                "shifted": abs(ratio) >= 0.08,
            }
        )
    return pd.DataFrame(rows)


def score_distribution_comparison(
    baseline_events: list[dict[str, object]], current_events: list[dict[str, object]]
) -> dict[str, float]:
    baseline = quality_snapshot(baseline_events)
    current = quality_snapshot(current_events)
    return {
        "baseline_average_score": baseline["average_score"],
        "current_average_score": current["average_score"],
        "average_score_delta": round(
            float(current["average_score"]) - float(baseline["average_score"]), 4
        ),
        "baseline_high_risk_rate": baseline["high_risk_rate"],
        "current_high_risk_rate": current["high_risk_rate"],
        "high_risk_rate_delta": round(
            float(current["high_risk_rate"]) - float(baseline["high_risk_rate"]), 4
        ),
    }


def trace_candidates(
    feature_comparison: pd.DataFrame,
    score_comparison: dict[str, float],
    quality_report: dict[str, object],
    current_events: list[dict[str, object]],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    shifted_features = feature_comparison.loc[
        feature_comparison["shifted"], "feature"
    ].tolist()
    if shifted_features:
        rows.append(
            {
                "candidate": "input_case_mix_shift",
                "evidence": f"shifted_features={', '.join(shifted_features)}",
                "owner": "Data Engineering",
                "next_action": "최근 입력 출처와 전처리 변경을 확인합니다.",
            }
        )
    if score_comparison["high_risk_rate_delta"] > 0.15:
        rows.append(
            {
                "candidate": "prediction_shift",
                "evidence": (
                    "high_risk_rate_delta="
                    f"{score_comparison['high_risk_rate_delta']:.4f}"
                ),
                "owner": "ML Engineering",
                "next_action": "점수 분포와 임계값 설정을 비교합니다.",
            }
        )
    if float(quality_report["error_rate_delta"]) > 0.03:
        failed = next(
            (event for event in current_events if event["validation_failure"]), {}
        )
        rows.append(
            {
                "candidate": "api_validation",
                "evidence": (
                    f"request_id={failed.get('request_id')}; "
                    f"failed_field={failed.get('failed_field')}"
                ),
                "owner": "Client Integration",
                "next_action": "검증 실패 필드와 입력 출처를 확인합니다.",
            }
        )
    if float(quality_report["latency_delta_ms"]) > 100:
        rows.append(
            {
                "candidate": "service_latency",
                "evidence": (
                    f"latency_delta_ms={quality_report['latency_delta_ms']:.1f}"
                ),
                "owner": "Platform/MLOps",
                "next_action": "서비스 부하와 배포 상태를 확인합니다.",
            }
        )
    return pd.DataFrame(rows)


def evaluate_release(
    report: dict[str, object], snapshot: dict[str, float | int], contract_passed: bool
) -> dict[str, object]:
    checks = [
        {
            "name": "precision",
            "observed": report["precision"],
            "criterion": ">= 0.6000",
            "passed": float(report["precision"]) >= 0.6,
        },
        {
            "name": "recall",
            "observed": report["recall"],
            "criterion": ">= 0.6000",
            "passed": float(report["recall"]) >= 0.6,
        },
        {
            "name": "error_rate",
            "observed": snapshot["error_rate"],
            "criterion": "<= 0.0500",
            "passed": float(snapshot["error_rate"]) <= 0.05,
        },
        {
            "name": "latency",
            "observed": snapshot["average_latency_ms"],
            "criterion": "<= 250.0000 ms",
            "passed": float(snapshot["average_latency_ms"]) <= 250,
        },
        {
            "name": "prepared_api_contract",
            "observed": contract_passed,
            "criterion": "is True",
            "passed": contract_passed,
        },
    ]
    failed = [check["name"] for check in checks if not check["passed"]]
    unresolved = ["live_deployment"]
    return {
        "recommendation": "conditional_hold" if failed or unresolved else "approve",
        "approved": not failed and not unresolved,
        "failed_checks": failed,
        "unresolved_risks": unresolved,
        "checks": checks,
        "notes": [
            "실패한 기준과 미검증 운영 리스크를 해소할 때까지 배포를 보류합니다."
        ],
        "re_evaluation_condition": (
            "owner별 evidence가 같은 approval rule을 통과하면 재평가합니다."
        ),
    }
