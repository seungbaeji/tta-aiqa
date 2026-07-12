"""Candidate release evaluation use case tests."""

import pytest
from aiqa_qa.application import evaluate_candidate_releases
from aiqa_qa.domain import Decision, ModelEvidence, ReleasePolicy


def evidence(profile: str, recall: float, false_negative: int) -> ModelEvidence:
    return ModelEvidence(
        profile=profile,
        precision=0.4,
        recall=recall,
        pr_auc=0.5,
        false_negative=false_negative,
        bootstrap_recall_lower=recall - 0.1,
    )


def test_candidates_are_evaluated_independently_against_baseline() -> None:
    policy = ReleasePolicy(
        name="test",
        disclaimer="education only",
        baseline_profile="baseline",
        candidate_a_profile="candidate-a",
        candidate_b_profile="candidate-b",
        minimum_recall=0.5,
        recall_safety_margin=0.05,
        minimum_recall_bootstrap_lower=0.4,
        minimum_precision=0.2,
        minimum_pr_auc_delta_vs_baseline=0,
        minimum_false_negative_reduction=10,
    )
    result = evaluate_candidate_releases(
        policy=policy,
        baseline=evidence("baseline", 0.2, 70),
        candidates=(
            evidence("candidate-a", 0.2, 70),
            evidence("candidate-b", 0.8, 20),
        ),
    )

    assert [item.decision for item in result.decisions] == [
        Decision.HOLD,
        Decision.APPROVE,
    ]


def test_release_evaluation_rejects_a_candidate_set_different_from_policy() -> None:
    policy = ReleasePolicy(
        name="test",
        disclaimer="education only",
        baseline_profile="baseline",
        candidate_a_profile="candidate-a",
        candidate_b_profile="candidate-b",
        minimum_recall=0.5,
        recall_safety_margin=0.05,
        minimum_recall_bootstrap_lower=0.4,
        minimum_precision=0.2,
        minimum_pr_auc_delta_vs_baseline=0,
        minimum_false_negative_reduction=10,
    )

    with pytest.raises(ValueError, match="candidate profiles"):
        evaluate_candidate_releases(
            policy=policy,
            baseline=evidence("baseline", 0.2, 70),
            candidates=(
                evidence("candidate-a", 0.2, 70),
                evidence("candidate-c", 0.8, 20),
            ),
        )
