"""Release evidence conversion and scenario invariants."""

from aiqa_model.domain import BenchmarkResult, ProfileEvaluation
from aiqa_qa.adapters import load_release_policy
from aiqa_qa.application import EvaluateCandidateReleases
from aiqa_qa.domain import Decision, ModelEvidence, ReleaseDecision

from model_trainer.settings import ModelTrainerSettings


def evaluate_release(
    settings: ModelTrainerSettings, result: BenchmarkResult
) -> tuple[ReleaseDecision, ReleaseDecision]:
    document, policy = load_release_policy(settings.release_policy_path)
    profiles = {item.profile: item for item in result.profiles}
    required = {
        document.baseline_profile,
        document.candidate_a_profile,
        document.candidate_b_profile,
    }
    if set(profiles) != required:
        raise ValueError("benchmark profiles do not match the release policy")
    baseline = _evidence(profiles[document.baseline_profile])
    evaluation = EvaluateCandidateReleases(policy).execute(
        baseline=baseline,
        candidates=(
            _evidence(profiles[document.candidate_a_profile]),
            _evidence(profiles[document.candidate_b_profile]),
        ),
    )
    return evaluation.decisions


def assert_teaching_scenario(decisions: tuple[ReleaseDecision, ...]) -> None:
    by_profile = {item.profile: item.decision for item in decisions}
    if by_profile != {
        "candidate-a": Decision.HOLD,
        "candidate-b": Decision.APPROVE,
    }:
        raise RuntimeError(
            "frozen teaching scenario failed; do not tune against the evaluation role: "
            f"{by_profile}"
        )


def teaching_scenario_matches(decisions: tuple[ReleaseDecision, ...]) -> bool:
    return {item.profile: item.decision for item in decisions} == {
        "candidate-a": Decision.HOLD,
        "candidate-b": Decision.APPROVE,
    }


def decisions_to_dict(
    decisions: tuple[ReleaseDecision, ...],
) -> list[dict[str, object]]:
    return [
        {
            "profile": item.profile,
            "decision": item.decision.value,
            "checks": dict(item.checks),
        }
        for item in decisions
    ]


def _evidence(evaluation: ProfileEvaluation) -> ModelEvidence:
    metrics = evaluation.metrics
    return ModelEvidence(
        profile=evaluation.profile,
        precision=metrics.precision,
        recall=metrics.recall,
        pr_auc=metrics.pr_auc,
        false_negative=metrics.false_negative,
        bootstrap_recall_lower=evaluation.bootstrap_recall_lower,
    )
