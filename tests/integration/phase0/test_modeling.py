import numpy as np
import pandas as pd
import pytest

from scripts.phase0.modeling import binary_metrics, select_modeling_roles


def test_binary_metrics_reports_concrete_confusion_counts() -> None:
    target = np.asarray([0, 0, 1, 1])
    probabilities = np.asarray([0.1, 0.8, 0.7, 0.2])

    metrics = binary_metrics(target, probabilities, threshold=0.5)

    assert metrics["confusion_matrix"] == {"tn": 1, "fp": 1, "fn": 1, "tp": 1}
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5


def test_modeling_roles_reject_final_test_access() -> None:
    frame = pd.DataFrame(
        {
            "record_id": [1, 2],
            "role": ["train", "test"],
        }
    )

    with pytest.raises(ValueError, match="sealed roles"):
        select_modeling_roles(frame, {"train", "test"})
