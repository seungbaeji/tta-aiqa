"""Safe extraction adapter for downloaded PhysioNet archives."""

import zipfile
from pathlib import Path


def extract_archive(archive_path: Path, destination: Path) -> None:
    """Extract a ZIP archive after rejecting unsafe member paths."""
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        if not members or any(
            Path(member.filename).is_absolute() or ".." in Path(member.filename).parts
            for member in members
        ):
            raise ValueError("archive contains an unsafe member path")
        archive.extractall(destination)
