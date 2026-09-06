"""JSON evidence serialization owned by the data-quality process."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RawValidationProfileDocument(BaseModel):
    """Stable raw-record quality measurements included in validation evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    records: int = Field(ge=0)
    observations: int = Field(ge=0)
    sentinels: int = Field(ge=0)
    maximum_minute: int = Field(ge=0)


class ProcessedValidationProfileDocument(BaseModel):
    """Stable processed-feature quality measurements included in validation evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rows: int = Field(ge=0)
    feature_count: int = Field(ge=0)
    top_missing_rates: dict[str, float]


class ValidationProfileDocument(BaseModel):
    """Raw and processed summary values written with a GE validation result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw: RawValidationProfileDocument
    processed: ProcessedValidationProfileDocument


class ValidationSummaryDocument(BaseModel):
    """Validated root DTO for one non-blocking data-quality validation artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    success: bool
    raw_ingestion: dict[str, Any]
    processed_readiness: dict[str, Any]
    profile: ValidationProfileDocument
    publish_blocking_gate: bool


def write_validation_summary(document: ValidationSummaryDocument, path: Path) -> None:
    """Persist one Great Expectations validation summary for the process."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
