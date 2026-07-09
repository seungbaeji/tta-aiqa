"""Chapter 2 Demo: create Great Expectations review artifacts."""

from __future__ import annotations

from ai_quality.common.config import load_yaml
from ai_quality.common.paths import artifact_path, config_path, data_path
from ai_quality.data_quality.application.build_validation_result import (
    build_validation_result,
)
from ai_quality.data_quality.application.inspect_dataset_quality import (
    InspectDatasetQuality,
)
from ai_quality.data_quality.domain.dataset_schema import DatasetSchema
from ai_quality.data_quality.domain.quality_rule import DataQualityRules
from ai_quality.data_quality.infrastructure.great_expectations_artifact_writer import (
    write_great_expectations_demo_artifacts,
)
from ai_quality.data_quality.infrastructure.pandas_dataset_reader import (
    PandasDatasetReader,
)


def main() -> None:
    """Write validation rule and report artifacts for instructor demo."""
    schema = DatasetSchema.from_config(
        load_yaml(config_path("validation", "dataset_schema.yaml"))
    )
    rules = DataQualityRules.from_config(
        load_yaml(config_path("validation", "data_quality_rules.yaml"))
    )
    expectations = load_yaml(
        config_path("validation", "great_expectations_rules.yaml")
    )["expectations"]

    report = InspectDatasetQuality(
        dataset_reader=PandasDatasetReader(schema),
        schema=schema,
        rules=rules,
    ).run(data_path("vital_signs_valid_degraded.csv"))
    validation_result = build_validation_result(
        report=report,
        expectations=expectations,
        dataset_name="vital_signs_valid_degraded.csv",
    )

    output_dir = artifact_path("great_expectations")
    artifacts = write_great_expectations_demo_artifacts(
        expectations=expectations,
        validation_result=validation_result,
        output_dir=output_dir,
    )

    print("Great Expectations demo artifacts")
    print(artifacts.expectations_path)
    print(artifacts.validation_result_path)
    print(artifacts.validation_summary_path)
    print(artifacts.data_docs_path)
    print("실패 규칙, 라벨(label), 범위 검증, QA 조치 기준을 확인합니다.")


if __name__ == "__main__":
    main()
