"""Validated deployed-model metadata adapter for the KServe scoring path."""

import json
from pathlib import Path
from typing import Any

from aiqa_serving.domain import ModelIdentity
from pydantic import BaseModel, ConfigDict, Field

MODEL_VERSION_DIGEST_LENGTH = 12
SHA256_PATTERN = r"^[0-9a-f]{64}$"


class FeatureContractMetadataDocument(BaseModel):
    """Feature-contract identity embedded in deployed model metadata."""

    model_config = ConfigDict(extra="allow", frozen=True)

    sha256: str = Field(pattern=SHA256_PATTERN)


class DeployedModelMetadataDocument(BaseModel):
    """Validated subset of one deployed model metadata document needed by Risk API."""

    model_config = ConfigDict(extra="allow", frozen=True)

    profile: str = Field(min_length=1)
    threshold: float
    model_sha256: str = Field(pattern=SHA256_PATTERN)
    feature_contract: FeatureContractMetadataDocument

    def to_model_identity(self) -> ModelIdentity:
        """Build the serving identity KServe must return for this deployed model."""
        return ModelIdentity(
            profile=self.profile,
            version=f"{self.profile}-{self.model_sha256[:MODEL_VERSION_DIGEST_LENGTH]}",
            threshold=self.threshold,
        )


def load_kserve_model_identity(
    path: Path,
    *,
    expected_feature_contract_sha256: str,
) -> ModelIdentity:
    """Load an identity only when metadata names the mounted feature contract."""
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("deployed model metadata root must be an object")
    metadata = DeployedModelMetadataDocument.model_validate(payload)
    if metadata.feature_contract.sha256 != expected_feature_contract_sha256:
        raise ValueError("KServe metadata feature contract hash mismatch")
    return metadata.to_model_identity()
