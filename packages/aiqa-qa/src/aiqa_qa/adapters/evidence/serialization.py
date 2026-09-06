"""Public conversion from release application values to JSON-safe evidence."""

from typing import Literal

from aiqa_qa.adapters.evidence.documents import ReleaseEvaluationEvidenceDocument
from aiqa_qa.application import ReleaseEvaluation


def release_evaluation_to_dict(
    result: ReleaseEvaluation,
    *,
    evaluation_role: Literal["valid", "test"],
    provenance: dict[str, str],
) -> dict[str, object]:
    """Convert a typed release evaluation into the reviewable JSON evidence schema."""
    return ReleaseEvaluationEvidenceDocument.from_application(
        result,
        evaluation_role=evaluation_role,
        provenance=provenance,
    ).model_dump(mode="json")
