"""Versioned configuration adapters."""

from aiqa_core.adapters.config.feature_contract import (
    FeatureContractDocument,
    load_feature_contract,
)

__all__ = ["FeatureContractDocument", "load_feature_contract"]
