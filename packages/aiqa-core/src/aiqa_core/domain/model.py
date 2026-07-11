"""Shared model identity values."""

from enum import StrEnum


class ModelRole(StrEnum):
    BASELINE = "baseline"
    CANDIDATE = "candidate"
    DEPLOYED = "deployed"
