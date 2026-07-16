"""Strict adapter-to-domain feature contract tests."""

from pathlib import Path

import pytest
from aiqa_core.adapters.config import FeatureContractDocument, load_feature_contract
from aiqa_core.domain import FeatureDefinition, FeatureSet, FeatureType
from pydantic import ValidationError


def valid_document() -> dict[str, object]:
    return {
        "schema_version": 1,
        "name": "candidate-v1",
        "target": "in_hospital_death",
        "features": [
            {"name": "age", "dtype": "float", "nullable": False},
            {"name": "icu_type", "dtype": "category", "nullable": False},
        ],
    }


def test_document_converts_to_framework_independent_domain() -> None:
    feature_set = FeatureContractDocument.model_validate(valid_document()).to_domain()

    assert feature_set.name == "candidate-v1"
    assert feature_set.feature_names == ("age", "icu_type")
    assert feature_set.features[1].dtype is FeatureType.CATEGORY


def test_unknown_configuration_key_is_rejected() -> None:
    document = valid_document()
    document["unexpected"] = True

    with pytest.raises(ValidationError):
        FeatureContractDocument.model_validate(document)


@pytest.mark.parametrize("invalid_name", ["in_hospital_death", "age"])
def test_target_and_duplicate_features_are_rejected(invalid_name: str) -> None:
    document = valid_document()
    features = document["features"]
    assert isinstance(features, list)
    features.append({"name": invalid_name, "dtype": "float", "nullable": True})

    with pytest.raises(ValueError):
        FeatureContractDocument.model_validate(document).to_domain()


def test_yaml_root_must_be_a_mapping(tmp_path: Path) -> None:
    path = tmp_path / "contract.yaml"
    path.write_text("- age\n", encoding="utf-8")

    with pytest.raises(ValueError, match="root must be a mapping"):
        load_feature_contract(path)


@pytest.mark.parametrize("value", ["float", 1])
def test_domain_feature_definition_rejects_non_enum_dtype(value: object) -> None:
    with pytest.raises(ValueError, match="feature dtype"):
        FeatureDefinition("age", value, False)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [0, "false"])
def test_domain_feature_definition_rejects_non_boolean_nullable(
    value: object,
) -> None:
    with pytest.raises(ValueError, match="feature nullable"):
        FeatureDefinition("age", FeatureType.FLOAT, value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("name", "target"),
    [
        (" feature-contract", "in_hospital_death"),
        ("feature-contract ", "in_hospital_death"),
        ("feature-contract", " in_hospital_death"),
        ("feature-contract", "in_hospital_death "),
    ],
)
def test_domain_feature_set_rejects_untrimmed_identifiers(
    name: str, target: str
) -> None:
    with pytest.raises(ValueError, match="must be non-empty and trimmed"):
        FeatureSet(
            schema_version=1,
            name=name,
            target=target,
            features=(FeatureDefinition("age", FeatureType.FLOAT, False),),
        )
