"""Development-only model evaluation use case."""

from aiqa_model.domain import BenchmarkResult, ModelProfileSelection
from aiqa_model.ports import DevelopmentModelEvaluator


def develop_models(
    *,
    selection: ModelProfileSelection,
    evaluator: DevelopmentModelEvaluator,
) -> BenchmarkResult:
    """Evaluate exactly the selected profiles on the train/valid lifecycle stage."""
    result = evaluator.evaluate_development(selection)
    profiles = tuple(item.profile for item in result.profiles)
    if profiles != selection.names:
        raise ValueError("development evidence profiles do not match the selection")
    return result
