"""Release evidence conversion and scenario invariants."""

from aiqa_model.domain import BenchmarkResult
from aiqa_qa.application import evaluate_candidate_releases
from aiqa_qa.domain import Decision, ReleaseDecision, ReleasePolicy

from model_trainer.application.release_evidence import model_evidence_from_profile

EXPECTED_TEACHING_DECISIONS = {
    "candidate-a": Decision.HOLD,
    "candidate-b": Decision.APPROVE,
}


def evaluate_release(
    policy: ReleasePolicy, result: BenchmarkResult
) -> tuple[ReleaseDecision, ReleaseDecision]:
    """Apply the configured QA policy to all benchmark profile evaluations."""
    profiles = {item.profile: item for item in result.profiles}
    required = set(policy.profile_names)
    if set(profiles) != required:
        raise ValueError("benchmark profiles do not match the release policy")
    baseline = model_evidence_from_profile(profiles[policy.baseline_profile])
    evaluation = evaluate_candidate_releases(
        policy=policy,
        baseline=baseline,
        candidates=(
            model_evidence_from_profile(profiles[policy.candidate_a_profile]),
            model_evidence_from_profile(profiles[policy.candidate_b_profile]),
        ),
    )
    return evaluation.decisions


def assert_teaching_scenario(decisions: tuple[ReleaseDecision, ...]) -> None:
    """Require the planned Candidate A hold and Candidate B approval outcome."""
    by_profile = {item.profile: item.decision for item in decisions}
    if by_profile != EXPECTED_TEACHING_DECISIONS:
        raise RuntimeError(
            "frozen teaching scenario failed; do not tune against the evaluation role: "
            f"{by_profile}"
        )


def teaching_scenario_matches(decisions: tuple[ReleaseDecision, ...]) -> bool:
    """Return whether final decisions reproduce the planned teaching scenario."""
    return (
        {item.profile: item.decision for item in decisions}
        == EXPECTED_TEACHING_DECISIONS
    )


def decisions_to_dict(
    decisions: tuple[ReleaseDecision, ...],
) -> list[dict[str, object]]:
    """Convert QA domain decisions into reviewable JSON-compatible values."""
    return [
        {
            "profile": item.profile,
            "decision": item.decision.value,
            "checks": dict(item.checks),
        }
        for item in decisions
    ]
