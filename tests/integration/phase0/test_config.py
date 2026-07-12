from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.phase0.config import load_config

CONFIG_PATH = Path("configs/phase0/physionet-2012.yaml")


def test_phase0_config_references_known_models() -> None:
    config = load_config(CONFIG_PATH)

    model_names = {model.name for model in config.evaluation.models}

    assert config.evaluation.baseline_profile in model_names
    assert set(config.evaluation.candidate_a_profiles) <= model_names
    assert set(config.evaluation.candidate_b_profiles) <= model_names


def test_phase0_config_rejects_unknown_keys(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(CONFIG_PATH.read_text() + "\nunknown: true\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config(invalid)
