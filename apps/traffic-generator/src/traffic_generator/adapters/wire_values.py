"""CSV scalar conversion for HTTP JSON request payloads."""

import pandas as pd
from aiqa_core.domain import FeatureType


def to_wire_value(value: object, dtype: FeatureType) -> object:
    """Convert one CSV cell to the declared feature-contract JSON value type."""
    if pd.isna(value):
        return None
    if dtype is FeatureType.BOOLEAN:
        return bool(int(float(value)))
    if dtype is FeatureType.INTEGER:
        return int(float(value))
    if dtype is FeatureType.FLOAT:
        return float(value)
    return float(value) if isinstance(value, int | float) else str(value)
