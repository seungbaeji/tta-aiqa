"""One-shot sealed-test model confirmation use case."""

from aiqa_model.domain import (
    BenchmarkResult,
    ModelProfileSelection,
    SealedTestConfirmation,
)
from aiqa_model.ports import FittedModels, FrozenModelEvaluator


def confirm_frozen_models(
    *,
    confirmation: SealedTestConfirmation,
    selection: ModelProfileSelection,
    evaluator: FrozenModelEvaluator,
    fitted_models: FittedModels,
) -> BenchmarkResult:
    """Score the exact frozen selection after explicit sealed-test acknowledgement."""
    if fitted_models.names != selection.names:
        raise ValueError("fitted model profiles do not match the sealed-test selection")
    result = evaluator.evaluate_frozen_models(selection, fitted_models)
    profiles = tuple(item.profile for item in result.profiles)
    if profiles != selection.names:
        raise ValueError("sealed-test evidence profiles do not match the selection")
    return result
