"""Quality report writer port."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ai_quality.data_quality.domain.quality_report import QualityReport


class QualityReportWriter(Protocol):
    """Write a quality report artifact."""

    def write(self, report: QualityReport, output_path: Path) -> Path:
        """Write a report and return the output path."""
        raise NotImplementedError
