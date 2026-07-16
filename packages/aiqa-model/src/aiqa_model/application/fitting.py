"""Frozen development-data model fitting use case."""

from aiqa_model.domain import ModelProfileSelection
from aiqa_model.ports import FittedModels, FrozenModelFitter


def fit_model_bundles(
    *,
    selection: ModelProfileSelection,
    fitter: FrozenModelFitter,
) -> FittedModels:
    """Fit exactly the selected configured profiles on train and valid data."""
    fitted_models = fitter.fit_models(selection)
    if fitted_models.names != selection.names:
        raise ValueError("fitted model profiles do not match the selection")
    return fitted_models
