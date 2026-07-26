"""Prepared incident evidence and learner handoff contract."""

import json
from pathlib import Path

import pandas as pd
import pytest
from aiqa_core.adapters.config import load_feature_contract
from aiqa_serving.adapters import LocalSklearnRiskScorer, sha256_file
from traffic_generator.adapters import CsvPatientPool, load_traffic_config
from traffic_generator.domain import apply_feature_transforms

EVIDENCE_PATH = Path("docs/reference/evidence/incident/initial-signal.json")


def test_initial_signal_can_seed_the_first_learner_evidence_row() -> None:
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    signals = {signal["scenario"]: signal for signal in evidence["signals"]}

    assert evidence["evidence_id"] == "E-01"
    assert evidence["scope"] == "prepared_course_evidence"
    assert evidence["source"]["live_telemetry"] is False
    assert "traffic_config" not in evidence["source"]
    assert evidence["model"] == {
        "profile": "baseline",
        "version": "baseline-f2576f12512a",
        "threshold": 0.5,
        "changed_between_scenarios": False,
    }
    assert evidence["sample"]["row_count"] == 100
    assert evidence["sample"]["same_base_rows_for_both_scenarios"] is True
    assert evidence["sample"]["target_present"] is False
    assert signals["baseline"]["high_risk_count"] == 3
    assert signals["baseline"]["high_risk_proportion"] == 0.03
    assert signals["current-shift"]["high_risk_count"] == 6
    assert signals["current-shift"]["high_risk_proportion"] == 0.06
    assert all(signal["telemetry_available"] is False for signal in signals.values())
    assert evidence["ground_truth"]["available"] is False
    assert all(
        signal["run_id"] in signal["representative_request_id"]
        for signal in signals.values()
    )
    assert "input condition" not in json.dumps(
        evidence["interpretation"], ensure_ascii=False
    )


def test_initial_signal_matches_the_frozen_sample_model_and_transforms() -> None:
    """Recompute E-01 when the course setup artifacts are available."""
    model_path = Path(
        "artifacts/models/revisions/v2/bundles/baseline/model.joblib"
    )
    data_path = Path(
        "data/splits/physionet-2012/revisions/v2/datasets/operational.csv"
    )
    if not model_path.is_file() or not data_path.is_file():
        pytest.skip("run scripts/setup_course.py to recompute prepared E-01")

    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    contract_path = Path("configs/contracts/model-input.yaml")
    contract = load_feature_contract(contract_path)
    scorer = LocalSklearnRiskScorer(
        model_path,
        sha256_file(contract_path),
    )
    pool = CsvPatientPool(data_path, contract)
    shift_plan = load_traffic_config(
        Path("configs/traffic/scenarios.yaml")
    ).plans()["current-shift"]
    baseline = [pool.patient(index) for index in range(pool.size)]
    shifted = [
        apply_feature_transforms(features, shift_plan.transforms)
        for features in baseline
    ]

    def scores(payloads: list[dict[str, object]]) -> pd.Series:
        return pd.Series(
            [
                scorer.score(tuple(payload.items()))
                for payload in payloads
            ]
        )

    expected = {signal["scenario"]: signal for signal in evidence["signals"]}
    observed = {
        "baseline": scores(baseline),
        "current-shift": scores(shifted),
    }

    assert scorer.identity.profile == evidence["model"]["profile"]
    assert scorer.identity.version == evidence["model"]["version"]
    assert scorer.identity.threshold == evidence["model"]["threshold"]
    assert pool.size == evidence["sample"]["row_count"]
    assert all(
        set(payload) == set(contract.feature_names) for payload in baseline
    )
    for scenario, scenario_scores in observed.items():
        high_risk_count = int(
            scenario_scores.ge(scorer.identity.threshold).sum()
        )
        assert high_risk_count == expected[scenario]["high_risk_count"]
        assert high_risk_count / len(scenario_scores) == (
            expected[scenario]["high_risk_proportion"]
        )
        assert round(float(scenario_scores.quantile(0.95)), 4) == (
            expected[scenario]["score_p95"]
        )


def test_release_record_names_the_working_and_submission_path() -> None:
    template = Path("labs/release-decision-record.md").read_text(encoding="utf-8")
    lab_guide = Path("labs/README.md").read_text(encoding="utf-8")

    assert "docs/reference/evidence/incident/initial-signal.json" in template
    assert "artifacts/reports/release-decision-record.md" in template
    assert "E-01" in template
    assert "`observation_window`" in template
    assert "`run_id`, `representative_request_id`" in template
    assert "`telemetry_available`, `identifier_scope`" in template
    assert "3/100" not in template
    assert "6/100" not in template
    assert (
        "test -f artifacts/reports/release-decision-record.md ||" in lab_guide
    )
    assert "uv sync --all-packages --group dev --group notebook" in lab_guide
    assert "uv run python scripts/setup_course.py --data-only" in lab_guide
    assert "Docker, Kubernetes나 대상 환경의 실행 근거로 쓰지 않습니다." in (
        lab_guide
    )


def test_observability_setup_preserves_an_existing_personal_environment() -> None:
    guide = Path("labs/ch04-observability/README.md").read_text(encoding="utf-8")

    assert "test -f .env.grafanacloud ||" in guide
    assert "cp .env.grafanacloud.example .env.grafanacloud" in guide


def test_serving_guide_only_requests_correlation_evidence_that_is_persisted() -> None:
    guide = Path("labs/ch03-serving/README.md").read_text(encoding="utf-8")

    assert "응답의 `X-Request-ID`" not in guide
    assert "`artifacts/traffic/*.jsonl`의 `request_id`" in guide
    assert "응답 본문의 `request_id`" in guide


def test_release_guide_separates_api_identity_from_deployment_digest() -> None:
    guide = Path("labs/ch05-release-decision/README.md").read_text(
        encoding="utf-8"
    )

    assert "대상 `/v1/model`의 프로필·버전·임계값" in guide
    assert "배포 선언 파일·오버레이에서는 전체 SHA-256 해시값" in guide
    assert "대상 `/v1/model`의 프로필, 해시값, 임계값" not in guide


@pytest.mark.parametrize(
    "path",
    (
        Path("labs/ch03-serving/README.md"),
        Path("labs/ch05-release-decision/README.md"),
    ),
)
def test_cluster_labs_stop_before_server_calls_on_context_mismatch(
    path: Path,
) -> None:
    guide = path.read_text(encoding="utf-8")

    assert 'test -n "${TARGET_CONTEXT:-}"' in guide
    assert 'CURRENT_CONTEXT="$(kubectl config current-context)"' in guide
    assert 'test "$CURRENT_CONTEXT" = "$TARGET_CONTEXT"' in guide
    assert 'kubectl --context "$TARGET_CONTEXT" apply --dry-run=server' in guide
