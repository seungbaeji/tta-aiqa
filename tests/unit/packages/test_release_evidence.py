"""Release evaluation evidence adapter tests."""

from aiqa_qa.adapters import release_evaluation_to_dict
from aiqa_qa.application import evaluate_candidate_releases
from aiqa_qa.domain import ModelEvidence, ReleasePolicy


def policy() -> ReleasePolicy:
    """Create a minimal release policy for evidence serialization."""
    return ReleasePolicy(
        name="test",
        disclaimer="education only",
        baseline_profile="baseline",
        candidate_a_profile="candidate-a",
        candidate_b_profile="candidate-b",
        minimum_recall=0.5,
        recall_safety_margin=0.05,
        minimum_recall_bootstrap_lower=0.4,
        minimum_precision=0.2,
        minimum_pr_auc_delta_vs_baseline=0.0,
        minimum_false_negative_reduction=10,
    )


def evidence(profile: str, recall: float, false_negative: int) -> ModelEvidence:
    """Create one valid model evidence value for a policy comparison."""
    return ModelEvidence(
        profile=profile,
        precision=0.4,
        recall=recall,
        pr_auc=0.5,
        false_negative=false_negative,
        bootstrap_recall_lower=recall - 0.1,
    )


def test_release_evidence_serializes_stable_check_names() -> None:
    result = evaluate_candidate_releases(
        policy=policy(),
        baseline=evidence("baseline", 0.2, 70),
        candidates=(
            evidence("candidate-a", 0.2, 70),
            evidence("candidate-b", 0.8, 20),
        ),
    )

    document = release_evaluation_to_dict(
        result,
        evaluation_role="valid",
        provenance={"profiles_sha256": "abc"},
    )

    assert document["baseline_profile"] == "baseline"
    assert document["decisions"][0]["checks"]["precision_floor"] is True
    assert document["decisions"][1]["decision"] == "APPROVE"
