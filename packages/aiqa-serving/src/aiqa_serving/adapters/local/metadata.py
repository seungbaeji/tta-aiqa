"""Pydantic view of model bundle metadata needed by the serving adapter."""

from pydantic import BaseModel, ConfigDict, Field


class BundleFeatureDocument(BaseModel):
    """One canonical model-input feature embedded in a model bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    dtype: str | None = None
    nullable: bool | None = None


class BundleFeatureContractDocument(BaseModel):
    """Feature-contract identity and ordered names embedded in a model bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str | None = None
    sha256: str
    features: tuple[BundleFeatureDocument, ...] = Field(min_length=1)


class LocalBundleMetadataDocument(BaseModel):
    """Forward-compatible validated subset of external model bundle metadata."""

    model_config = ConfigDict(extra="allow", frozen=True)

    profile: str
    threshold: float
    feature_contract: BundleFeatureContractDocument
