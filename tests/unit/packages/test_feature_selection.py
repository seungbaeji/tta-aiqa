"""Versioned model feature-selection contract tests."""

from pathlib import Path

import pytest
from aiqa_core.adapters.config import load_feature_contract
from aiqa_model.adapters import load_feature_set_catalog
from aiqa_model.application import resolve_feature_set
from aiqa_model.domain import (
    FeatureSelectionStrategy,
    FeatureSetCatalog,
    SelectedFeatureSet,
)


def test_v1_and_v2_feature_set_documents_resolve_the_canonical_contract() -> None:
    """Both supported config shapes must actively select the full model contract."""
    contract = load_feature_contract(Path("configs/contracts/model-input.yaml"))

    for path in (
        Path("configs/model/feature-sets.yaml"),
        Path("configs/model/revisions/v2/feature-sets.yaml"),
    ):
        catalog = load_feature_set_catalog(path)
        selected = resolve_feature_set(feature_contract=contract, catalog=catalog)

        assert selected is contract


def test_feature_set_catalog_rejects_an_unknown_canonical_name() -> None:
    """A frozen selection policy must name one declared feature-set definition."""
    with pytest.raises(ValueError, match="canonical feature set"):
        FeatureSetCatalog(
            canonical_feature_set="missing",
            feature_sets=(
                SelectedFeatureSet(
                    name="full",
                    strategy=FeatureSelectionStrategy.ALL_FROM_MODEL_INPUT_CONTRACT,
                    rationale="unit-test",
                ),
            ),
        )
