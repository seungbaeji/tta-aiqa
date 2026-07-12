"""Release decision domain tests."""

from pathlib import Path

from aiqa_qa.adapters import load_release_policy
from aiqa_qa.domain import Decision, ModelEvidence, decide_release


def evidence(
    profile: str,
    *,
    precision: float,
    recall: float,
    pr_auc: float,
    false_negative: int,
    bootstrap_recall_lower: float,
) -> ModelEvidence:
    return ModelEvidence(
        profile=profile,
        precision=precision,
        recall=recall,
        pr_auc=pr_auc,
        false_negative=false_negative,
        bootstrap_recall_lower=bootstrap_recall_lower,
    )


def test_phase0_candidate_a_is_held_and_candidate_b_is_approved() -> None:
    _, policy = load_release_policy(Path("configs/qa/release-policy.yaml"))
    baseline = evidence(
        "baseline",
        precision=0.381,
        recall=0.193,
        pr_auc=0.351,
        false_negative=67,
        bootstrap_recall_lower=0.114,
    )
    candidate_a = evidence(
        "candidate-a",
        precision=0.615,
        recall=0.193,
        pr_auc=0.426,
        false_negative=67,
        bootstrap_recall_lower=0.114,
    )
    candidate_b = evidence(
        "candidate-b",
        precision=0.339,
        recall=0.783,
        pr_auc=0.412,
        false_negative=18,
        bootstrap_recall_lower=0.692,
    )

    assert decide_release(policy, baseline, candidate_a).decision is Decision.HOLD
    assert decide_release(policy, baseline, candidate_b).decision is Decision.APPROVE


def test_candidate_is_held_when_any_required_guardrail_fails() -> None:
    _, policy = load_release_policy(Path("configs/qa/release-policy.yaml"))
    baseline = evidence(
        "baseline",
        precision=0.4,
        recall=0.3,
        pr_auc=0.4,
        false_negative=60,
        bootstrap_recall_lower=0.2,
    )
    candidate = evidence(
        "candidate",
        precision=0.19,
        recall=0.8,
        pr_auc=0.5,
        false_negative=20,
        bootstrap_recall_lower=0.7,
    )

    decision = decide_release(policy, baseline, candidate)

    assert decision.decision is Decision.HOLD
    assert dict(decision.checks)["precision_floor"] is False
