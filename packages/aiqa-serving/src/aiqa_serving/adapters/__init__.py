"""Serving technology adapters."""

from aiqa_serving.adapters.kserve_http import KServeRiskScorer
from aiqa_serving.adapters.local_sklearn import LocalSklearnRiskScorer

__all__ = [
    "KServeRiskScorer",
    "LocalSklearnRiskScorer",
]
