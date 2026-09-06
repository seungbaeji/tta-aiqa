"""KServe V2 inference request payload construction."""

import json

from aiqa_serving.domain import FeatureValue


def inference_payload(
    features: tuple[tuple[str, FeatureValue], ...]
) -> dict[str, object]:
    """Build one KServe V2 BYTES input that carries the canonical feature mapping."""
    return {
        "inputs": [
            {
                "name": "features",
                "shape": [1],
                "datatype": "BYTES",
                "data": [json.dumps(dict(features), separators=(",", ":"))],
            }
        ]
    }
