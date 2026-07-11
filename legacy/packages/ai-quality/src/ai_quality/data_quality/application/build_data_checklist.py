"""Build a QA checklist from a quality report."""

from __future__ import annotations

from dataclasses import dataclass

from ai_quality.data_quality.domain.quality_report import QualityReport


@dataclass(frozen=True)
class ChecklistItem:
    """Single QA checklist item."""

    name: str
    passed: bool
    detail: str


class BuildDataChecklist:
    """Create the final data checklist used at the end of chapter 1."""

    def run(self, report: QualityReport) -> list[ChecklistItem]:
        """Return checklist items from a quality report."""
        return [
            ChecklistItem(
                name="required columns",
                passed=not report.missing_columns,
                detail=(
                    ", ".join(report.missing_columns)
                    or "all required columns exist"
                ),
            ),
            ChecklistItem(
                name="allowed labels",
                passed=report.label_support.invalid_count == 0,
                detail=f"invalid labels: {report.label_support.invalid_count}",
            ),
            ChecklistItem(
                name="label missing",
                passed=report.label_support.missing_count == 0,
                detail=f"missing labels: {report.label_support.missing_count}",
            ),
            ChecklistItem(
                name="positive support",
                passed=report.label_support.positive_count > 0,
                detail=(
                    f"{report.label_support.positive_label}: "
                    f"{report.label_support.positive_count}"
                ),
            ),
        ]
