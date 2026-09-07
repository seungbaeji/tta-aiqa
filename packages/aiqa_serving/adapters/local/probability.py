"""Local model probability output validation."""

from math import isfinite
from typing import Any


def positive_class_probability(probabilities: Any) -> float:
    """Extract and validate the positive-class probability from sklearn output."""
    try:
        value = probabilities[0, 1]
    except (IndexError, KeyError, TypeError) as error:
        raise ValueError(
            "local model does not return binary class probabilities"
        ) from error
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("local model positive-class probability is invalid")
    probability = float(value)
    if not isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("local model positive-class probability is outside [0, 1]")
    return probability
