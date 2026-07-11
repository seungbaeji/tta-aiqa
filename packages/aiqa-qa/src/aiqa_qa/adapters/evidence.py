"""JSON-safe release evidence adapter."""

from aiqa_qa.application import ReleaseEvaluation


def release_evaluation_to_dict(
    result: ReleaseEvaluation,
    *,
    evaluation_role: str,
    provenance: dict[str, str],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "evaluation_role": evaluation_role,
        "baseline_profile": result.baseline.profile,
        "decisions": [
            {
                "profile": decision.profile,
                "decision": decision.decision.value,
                "checks": dict(decision.checks),
            }
            for decision in result.decisions
        ],
        "provenance": provenance,
    }
