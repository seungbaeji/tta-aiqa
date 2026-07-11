"""Strict Risk API configuration adapter."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ApiConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    title: str = Field(min_length=1)
    api_version: str = Field(pattern=r"^v[1-9][0-9]*$")
    request_id_header: str = Field(min_length=1)
    scenario_header: str = Field(min_length=1)
    positive_label: str = Field(min_length=1)
    negative_label: str = Field(min_length=1)
    score_decimal_places: int = Field(ge=0, le=12)
    education_only: bool


def load_api_config(path: Path) -> ApiConfig:
    with path.open(encoding="utf-8") as file:
        payload: Any = yaml.safe_load(file)
    if not isinstance(payload, dict):
        raise ValueError("Risk API config root must be a mapping")
    return ApiConfig.model_validate(payload)
