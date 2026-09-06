"""PhysioNet source gateway owned by the Data Quality Pipeline process."""

from dataclasses import dataclass
from pathlib import Path

from aiqa_data.adapters import (
    PhysioNetSourceConfig,
    extract_archive,
    verify_source_manifest,
    write_source_integrity_report,
)
from aiqa_data.domain import SourceIntegrityReport


@dataclass(frozen=True)
class PhysioNetSourceGateway:
    """Bind source verification and archive extraction to one source contract."""

    source: PhysioNetSourceConfig

    def verify(self) -> SourceIntegrityReport:
        """Verify all manifest files and return typed source integrity evidence."""
        return verify_source_manifest(self.source.source_manifest_path)

    def write_evidence(self, report: SourceIntegrityReport, path: Path) -> None:
        """Persist the verified official-source evidence at the requested path."""
        write_source_integrity_report(report, path)

    def extract(self) -> None:
        """Extract the verified Set A archive into the records parent directory."""
        report = self.verify()
        archive_name = next(
            item.path for item in report.files if item.path == "set-a.zip"
        )
        extract_archive(
            self.source.source_manifest_path.parent / archive_name,
            self.source.records_dir.parent,
        )
