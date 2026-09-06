"""Prepared observability fallback artifact and learner guide contracts."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

FALLBACK_PATH = Path(
    "docs/reference/evidence/incident/prepared-observability-correlation.json"
)
GUIDE_PATH = Path("labs/ch04-observability/README.md")
HEX_TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
HEX_SPAN_ID = re.compile(r"^[0-9a-f]{16}$")
EXPECTED_SCENARIOS = {"baseline", "current-shift", "invalid"}
EXPECTED_CASES = {"normal", "slow", "invalid_422"}


def _normalized(text: str) -> str:
    """Collapse Markdown line wrapping for semantic prose assertions."""
    return " ".join(text.split())


def _heading_section(markdown: str, level: int, heading: str) -> str:
    """Return one Markdown heading section up to its next peer heading."""
    marks = "#" * level
    match = re.search(
        rf"^{marks} {re.escape(heading)}\n(.*?)(?=^{marks} |\Z)",
        markdown,
        flags=re.DOTALL | re.MULTILINE,
    )
    assert match is not None, heading
    return match.group(1)


def load_fallback() -> dict[str, Any]:
    """Load the prepared correlation bundle from its learner-facing path."""
    return json.loads(FALLBACK_PATH.read_text(encoding="utf-8"))


def _utc_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo == UTC
    return parsed


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(
            *( _all_keys(item) for item in value.values() )
        )
    if isinstance(value, list):
        return set().union(*(_all_keys(item) for item in value))
    return set()


def test_fallback_is_explicitly_offline_and_contains_no_sensitive_input() -> None:
    artifact = load_fallback()

    assert artifact["schema_version"] == 2
    assert artifact["classification"] == "PREPARED/OFFLINE"
    assert artifact["live_telemetry"] is False
    assert artifact["provenance"] == {
        "source_kind": "course_static_fixture",
        "captured_from_live_backend": False,
        "contains_raw_features": False,
        "contains_secrets": False,
        "intended_use": "offline collection handoff and bounded analysis",
    }
    assert any(
        "실시간 자료가 아닙니다" in limitation
        for limitation in artifact["limitations"]
    )
    assert any(
        "입증하지 않습니다" in limitation
        for limitation in artifact["limitations"]
    )
    assert not {
        "features",
        "payload",
        "patient",
        "error_message",
        "exception",
        "stacktrace",
        "token",
        "api_key",
    }.intersection(_all_keys(artifact))


def test_fallback_has_one_bounded_dashboard_packet_for_three_scenarios() -> None:
    artifact = load_fallback()
    window = artifact["observation_window"]
    start = _utc_timestamp(window["start"])
    end = _utc_timestamp(window["end"])
    assert start < end
    assert window["timezone"] == "UTC"
    assert artifact["environment"] == {
        "name": "prepared-offline",
        "scope": "static",
    }
    assert artifact["handoff_contract"] == {
        "live_manifest_path": "artifacts/traffic/collection-session.json",
        "live_scenario_artifact_path": "artifacts/traffic/compose.jsonl",
        "offline_packet_path": str(FALLBACK_PATH),
        "session_id": "OBS-FALLBACK-02",
        "scope": "static",
    }
    assert artifact["model"] == {
        "profile": "baseline",
        "version": "baseline-f2576f12512a",
        "threshold": 0.5,
    }

    summaries = {
        item["scenario"]: item
        for item in artifact["dashboard"]["scenario_summaries"]
    }
    assert set(summaries) == EXPECTED_SCENARIOS
    for scenario, summary in summaries.items():
        assert summary["run_id"].startswith(f"prepared-{scenario}")
        assert sum(summary["status_counts"].values()) == (
            summary["request_count"]
        )
        assert 0 <= summary["high_risk_prediction_rate"] <= 1
        assert summary["high_risk_prediction_count"] <= (
            summary["request_count"]
        )
        assert summary["missing_features_p95"] >= 0
        assert summary["latency_p95_ms"] >= 0
        if scenario == "invalid":
            assert summary["status_counts"] == {"200": 0, "422": 3, "5xx": 0}
            assert summary["score_p95"] is None
        else:
            assert summary["status_counts"]["200"] == summary["request_count"]
            assert isinstance(summary["score_p95"], float)

    series = artifact["dashboard"]["time_series"]
    assert 3 <= len(series) <= 12
    assert {point["scenario"] for point in series} == EXPECTED_SCENARIOS
    assert all(start <= _utc_timestamp(point["timestamp"]) <= end for point in series)
    assert all(
        {
            "request_count",
            "status_200",
            "status_422",
            "status_5xx",
            "high_risk_prediction_rate",
            "score_p95",
            "missing_features_p95",
            "latency_p95_ms",
        }.issubset(point)
        for point in series
    )


def test_fallback_correlates_normal_slow_and_422_logs_with_trace_paths() -> None:
    artifact = load_fallback()
    cases = {
        item["case"]: item for item in artifact["representative_requests"]
    }

    assert set(cases) == EXPECTED_CASES
    assert cases["normal"]["scenario"] == "baseline"
    assert cases["slow"]["scenario"] == "current-shift"
    assert cases["invalid_422"]["scenario"] == "invalid"
    assert [cases[name]["http"]["status_code"] for name in (
        "normal",
        "slow",
        "invalid_422",
    )] == [200, 200, 422]
    assert cases["slow"]["http"]["duration_ms"] > (
        artifact["selection_rules"]["slow_request_minimum_ms"]
    )

    for case in cases.values():
        correlation = case["correlation"]
        event = case["bounded_log_event"]
        spans = case["trace_path"]
        assert correlation["run_id"] in correlation["request_id"]
        assert HEX_TRACE_ID.fullmatch(correlation["trace_id"])
        assert event["run_id"] == correlation["run_id"]
        assert event["request_id"] == correlation["request_id"]
        assert event["trace_id"] == correlation["trace_id"]
        assert [span["span_name"] for span in spans] == [
            "traffic.generate",
            "risk-api.predict",
            "POST /v1/predict",
            "risk.predict",
        ]
        assert spans[0]["parent_span_id"] is None
        for parent, child in zip(spans[:-1], spans[1:], strict=True):
            assert HEX_SPAN_ID.fullmatch(parent["span_id"])
            assert child["parent_span_id"] == parent["span_id"]
        assert HEX_SPAN_ID.fullmatch(spans[-1]["span_id"])
        assert {span["trace_id"] for span in spans} == {
            correlation["trace_id"]
        }

    invalid = cases["invalid_422"]
    assert invalid["http"]["error"] == {
        "code": "MODEL_INPUT_INVALID",
        "validation_category": "missing",
    }
    assert invalid["bounded_log_event"]["event"] == (
        "model.input.validation.failed"
    )
    assert invalid["bounded_log_event"]["error_code"] == (
        "MODEL_INPUT_INVALID"
    )


def test_guide_links_packet_and_separates_p5_p6_p7() -> None:
    guide = GUIDE_PATH.read_text(encoding="utf-8")
    preparation = _heading_section(guide, 2, "관측")
    traffic = _heading_section(guide, 2, "traffic")
    p5 = _heading_section(
        traffic,
        3,
        "baseline·current-shift·invalid traffic의 의도와 상태 코드를 인계한다",
    )
    p6 = _heading_section(
        traffic,
        3,
        "선택한 대표 요청이 지표·로그·trace의 동일 사건으로 연결되는지 P6에 판정한다",
    )

    assert "PREPARED/OFFLINE" in guide
    assert str(FALLBACK_PATH) in guide
    assert "reference fixture" in guide
    assert "실제 Loki/Tempo 검색으로 바꾸지" in guide
    assert "secret과 token은 기록하지 않습니다" in preparation
    assert "course_preflight.py" not in preparation
    assert "aiqa-grafana-dashboard" not in preparation
    assert "\n  build\n" not in preparation
    assert "\n  up -d\n" in p5
    assert "up -d --build" not in p5
    assert "aiqa-grafana-dashboard" not in p5
    assert p5.count('\n  --user "$(id -u):$(id -g)"') == 2
    assert "course-session --scope local" in p5
    assert "`not_checked`" in p5
    assert "course-session-status" in p5
    assert "--session-id '<course-session 출력의 session_id>'" in p5
    assert "--dashboard-url" in p5
    assert "--prometheus available" in p5
    assert "--loki available" in p5
    assert "--tempo available" in p5
    assert "사람이 확인한 경우에만" in p5
    assert "확인하지 않은 옵션은 명령에 넣지 않아 `not_checked`" in p5
    assert "artifacts/traffic/collection-session.json" in guide
    assert "artifacts/traffic/compose.jsonl" in guide
    assert "invalid --run-id learner-observe-01" not in guide
    assert (
        '{service_name="risk-api", environment="<ENVIRONMENT>"} | json | '
        'run_id="<RUN_ID>" | request_id="<REQUEST_ID>"'
    ) in p6
    assert (
        'resource.service.name = "risk-api" && '
        'span."aiqa.run_id" = "<RUN_ID>" && '
        'span."aiqa.request_id" = "<REQUEST_ID>"'
    ) in p6
    assert "P6에서 P5 묶음" in p6
    assert "실제 Loki/Tempo 검색으로 바꾸지" in p6
    normalized = _normalized(guide)
    for completion in (
        "P5 인계 점검",
        "범위를 복원",
        "세 시나리오를 비교",
        "대표 요청을 선택",
        "E-05에 인계",
    ):
        assert completion in normalized
    assert "span_id, parent_span_id" in p6
    assert "P5 수집이 끝나도 P6와 P7이 끝날 때까지 Compose를 내리지" in normalized


def test_learner_materials_use_completion_gates_instead_of_fixed_minutes() -> None:
    paths = (
        Path("labs/README.md"),
        Path("labs/ch04-observability/README.md"),
        Path("labs/ch05-release-decision/README.md"),
    )
    text = _normalized(
        "\n".join(path.read_text(encoding="utf-8") for path in paths)
    )

    for fixed_pacing in (
        "30분 분석",
        "30분 동안",
        "40분 안",
        "0~5분",
        "5~15분",
        "15~25분",
        "25~30분",
    ):
        assert fixed_pacing not in text
    for completion_gate in (
        "인계 점검",
        "범위를 복원",
        "세 시나리오를 비교",
        "대표 요청을 선택",
        "E-05에 인계",
    ):
        assert completion_gate in text


def test_all_learner_compose_traffic_commands_use_the_host_identity() -> None:
    paths = (
        Path("README.md"),
        Path("apps/traffic-generator/README.md"),
        *Path("labs").rglob("*.md"),
    )
    commands: list[tuple[Path, str]] = []
    for path in paths:
        markdown = path.read_text(encoding="utf-8")
        for block in re.findall(r"```bash\n(.*?)```", markdown, flags=re.DOTALL):
            normalized = re.sub(r"\\\n\s*", " ", block)
            commands.extend(
                (path, match.group())
                for match in re.finditer(
                    r"docker compose\b.*?\btraffic-generator\b",
                    normalized,
                )
            )

    assert commands
    for path, command in commands:
        assert '--user "$(id -u):$(id -g)"' in command, path

    serving = Path("labs/ch03-serving/README.md").read_text(encoding="utf-8")
    observability = GUIDE_PATH.read_text(encoding="utf-8")
    assert "traffic-generator" not in serving
    assert "course-session --scope local" in observability
