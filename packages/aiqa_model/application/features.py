"""Feature-selection use case for a versioned model input contract."""

from aiqa_core.domain import FeatureSet

from aiqa_model.domain.features import FeatureSelectionStrategy, FeatureSetCatalog


def resolve_feature_set(
    *,
    feature_contract: FeatureSet,
    catalog: FeatureSetCatalog,
) -> FeatureSet:
    """Resolve the frozen selection policy into the canonical model feature contract."""
    if (
        catalog.canonical.strategy
        is FeatureSelectionStrategy.ALL_FROM_MODEL_INPUT_CONTRACT
    ):
        return feature_contract
    raise ValueError("unsupported feature-selection strategy")
