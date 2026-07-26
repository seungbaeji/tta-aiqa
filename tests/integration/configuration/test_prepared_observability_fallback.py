"""Prepared observability fallback artifact and learner guide contracts."""

import json
import re
from pathlib import Path
from typing import Any

FALLBACK_PATH = Path(
    "docs/reference/evidence/incident/prepared-observability-correlation.json"
)
GUIDE_PATH = Path("labs/ch04-observability/README.md")
HEX_TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
HEX_SPAN_ID = re.compile(r"^[0-9a-f]{16}$")


def load_fallback() -> dict[str, Any]:
    """Load the prepared correlation bundle from its learner-facing path."""
    return json.loads(FALLBACK_PATH.read_text(encoding="utf-8"))


def test_fallback_is_explicitly_offline_and_contains_no_raw_input() -> None:
    artifact = load_fallback()
    serialized = json.dumps(artifact, ensure_ascii=False).lower()

    assert artifact["classification"] == "PREPARED/OFFLINE"
    assert artifact["live_telemetry"] is False
    assert any(
        "실시간 자료가 아닙니다" in limitation
        for limitation in artifact["limitations"]
    )
    assert any(
        "입증하지 않습니다" in limitation
        for limitation in artifact["limitations"]
    )
    for forbidden in (
        '"features"',
        '"payload"',
        '"patient"',
        '"error_message"',
        '"exception"',
        '"stacktrace"',
    ):
        assert forbidden not in serialized


def test_fallback_correlates_run_request_log_and_trace_path() -> None:
    artifact = load_fallback()
    correlation = artifact["correlation"]
    event = artifact["bounded_log_event"]
    spans = artifact["trace_path"]

    assert correlation["scenario"] == "invalid"
    assert correlation["run_id"] in correlation["request_id"]
    assert HEX_TRACE_ID.fullmatch(correlation["trace_id"])
    assert [span["span_name"] for span in spans] == [
        "traffic.generate",
        "risk-api.predict",
        "POST /v1/predict",
        "risk.predict",
    ]
    assert [span["span_kind"] for span in spans] == [
        "INTERNAL",
        "CLIENT",
        "SERVER",
        "INTERNAL",
    ]
    assert [span["service_name"] for span in spans] == [
        "traffic-generator",
        "traffic-generator",
        "risk-api",
        "risk-api",
    ]
    assert {span["trace_id"] for span in spans} == {
        correlation["trace_id"]
    }
    assert spans[0]["parent_span_id"] is None
    for parent, child in zip(spans[:-1], spans[1:], strict=True):
        assert HEX_SPAN_ID.fullmatch(parent["span_id"])
        assert child["parent_span_id"] == parent["span_id"]
    assert HEX_SPAN_ID.fullmatch(spans[-1]["span_id"])

    for span in spans:
        assert span["attributes"]["aiqa.run_id"] == correlation["run_id"]
        assert span["attributes"]["aiqa.scenario"] == correlation["scenario"]
    for span in spans[1:]:
        assert (
            span["attributes"]["aiqa.request_id"]
            == correlation["request_id"]
        )

    assert event["run_id"] == correlation["run_id"]
    assert event["request_id"] == correlation["request_id"]
    assert event["trace_id"] == correlation["trace_id"]
    assert event["span_id"] == spans[-1]["span_id"]


def test_fallback_422_event_uses_only_the_bounded_error_contract() -> None:
    artifact = load_fallback()
    result = artifact["http_result"]
    event = artifact["bounded_log_event"]

    assert result == {
        "status_code": 422,
        "detail": {
            "code": "MODEL_INPUT_INVALID",
            "validation_category": "missing",
            "message": "model input does not match the public contract",
        },
    }
    assert event["event"] == "model.input.validation.failed"
    assert event["operation"] == "risk.predict"
    assert event["error_code"] == result["detail"]["code"]
    assert event["validation_category"] == (
        result["detail"]["validation_category"]
    )
    assert event["validation_category"] in {"missing", "extra", "type", "other"}
    assert set(event) == {
        "level",
        "message",
        "event",
        "service_name",
        "service_namespace",
        "environment",
        "operation",
        "scenario",
        "run_id",
        "request_id",
        "trace_id",
        "span_id",
        "error_code",
        "validation_category",
    }


def test_guide_links_fallback_and_copy_paste_live_queries() -> None:
    guide = GUIDE_PATH.read_text(encoding="utf-8")

    assert "[PREPARED/OFFLINE]" in guide
    assert str(FALLBACK_PATH) in guide
    assert "실제 수집 자료가 아니라" in guide
    assert "invalid --run-id learner-observe-01" in guide
    assert (
        '{service_name="risk-api", environment="compose"} | json | '
        'run_id="learner-observe-01" | '
        'request_id="invalid-learner-observe-01-0001"'
    ) in guide
    assert (
        'resource.service.name = "risk-api" && '
        'span."aiqa.run_id" = "learner-observe-01" && '
        'span."aiqa.request_id" = '
        '"invalid-learner-observe-01-0001"'
    ) in guide
