"""Build the chapter 1 data quality report artifact."""

from __future__ import annotations

from pathlib import Path

from ai_quality.common.artifacts import ensure_artifact_dir
from ai_quality.data_quality.application.inspect_dataset_quality import (
    InspectDatasetQuality,
)
from ai_quality.data_quality.infrastructure.markdown_report_writer import (
    MarkdownQualityReportWriter,
)
from ai_quality.data_quality.infrastructure.pandas_dataset_reader import (
    PandasDatasetReader,
)
from ai_quality.labs.ch01_data_quality import (
    chapter_dataset_path,
    load_rules,
    load_schema,
)


def main() -> None:
    """Build the chapter 1 quality report."""
    schema = load_schema()
    rules = load_rules()
    dataset_path = chapter_dataset_path()
    if not dataset_path.exists():
        msg = (
            f"Dataset not found: {dataset_path}\n"
            "Run: uv run python labs/prepare_data.py"
        )
        raise FileNotFoundError(msg)

    report = InspectDatasetQuality(
        dataset_reader=PandasDatasetReader(schema),
        schema=schema,
        rules=rules,
    ).run(dataset_path)

    output_path: Path = ensure_artifact_dir("reports") / "chapter_01_quality_report.md"
    MarkdownQualityReportWriter().write(report, output_path)

    print(f"written_report={output_path}")
    print(f"row_count={report.row_count}")
    print(f"evaluation_ready={report.is_evaluation_ready}")


if __name__ == "__main__":
    main()
