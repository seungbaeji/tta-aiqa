"""Model configuration loading functions."""

from pathlib import Path

from aiqa_model.adapters.config.documents import (
    EvaluationDocument,
    FeatureSetsDocument,
    ProfilesDocument,
)
from aiqa_model.adapters.config.yaml import load_yaml_mapping
from aiqa_model.domain import EvaluationPlan, FeatureSetCatalog, ModelProfileCatalog


def load_model_profiles(path: Path) -> ModelProfileCatalog:
    """Load one strict profile document into a typed model-profile catalog."""
    return ProfilesDocument.model_validate(load_yaml_mapping(path)).to_domain()


def load_evaluation_plan(path: Path) -> EvaluationPlan:
    """Load one strict evaluation document into the model evaluation plan."""
    return EvaluationDocument.model_validate(load_yaml_mapping(path)).to_domain()


def load_feature_set_catalog(path: Path) -> FeatureSetCatalog:
    """Load one V1/V2 feature-selection document into its typed domain catalog."""
    return FeatureSetsDocument.model_validate(load_yaml_mapping(path)).to_domain()
