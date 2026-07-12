"""Traffic configuration and V2 patient pool adapter tests."""

from pathlib import Path

from aiqa_core.adapters.config import load_feature_contract
from traffic_generator.adapters import CsvPatientPool, load_traffic_config
from traffic_generator.domain import ScenarioMode


def test_versioned_config_defines_all_four_course_scenarios() -> None:
    config = load_traffic_config(Path("configs/traffic/scenarios.yaml"))
    plans = config.plans()

    assert set(plans) == {
        "baseline",
        "approved-candidate",
        "current-shift",
        "invalid",
    }
    assert plans["baseline"].mode is ScenarioMode.VALID
    assert plans["current-shift"].mode is ScenarioMode.SHIFT
    assert plans["invalid"].mode is ScenarioMode.INVALID


def test_v2_operational_pool_is_target_free_and_wire_compatible() -> None:
    contract = load_feature_contract(Path("configs/contracts/model-input.yaml"))
    pool = CsvPatientPool(
        Path("data/splits/physionet-2012/revisions/v2/datasets/operational.csv"),
        contract,
    )

    patient = pool.patient(0)
    assert pool.size == 100
    assert set(patient) == set(contract.feature_names)
    assert isinstance(patient["age__missing"], bool)
    assert "target" not in patient
