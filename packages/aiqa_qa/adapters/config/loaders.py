"""Release policy configuration loading functions."""

from pathlib import Path

from aiqa_qa.adapters.config.documents import ReleasePolicyDocument
from aiqa_qa.adapters.config.yaml import load_yaml_mapping
from aiqa_qa.domain import ReleasePolicy


def load_release_policy(path: Path) -> ReleasePolicy:
    """Load a strict versioned YAML document into a typed release policy."""
    return ReleasePolicyDocument.model_validate(load_yaml_mapping(path)).to_domain()
