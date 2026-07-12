"""Candidate release evaluation use case tests."""

from aiqa_qa.application import EvaluateCandidateReleases
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
        minimum_recall=0.5,
        recall_safety_margin=0.05,
        minimum_recall_bootstrap_lower=0.4,
        minimum_precision=0.2,
        minimum_pr_auc_delta_vs_baseline=0,
        minimum_false_negative_reduction=10,
    )
    use_case = EvaluateCandidateReleases(policy)

    result = use_case.execute(
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
