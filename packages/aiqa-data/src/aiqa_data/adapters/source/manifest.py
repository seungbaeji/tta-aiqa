"""Manifest validation, acquisition, and integrity evidence adapters."""

from collections.abc import Callable
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from aiqa_data.adapters.source.checksum import (
    matches_expected_file,
    sha256_bytes,
    sha256_file,
)
from aiqa_data.adapters.source.download import download_bytes
from aiqa_data.adapters.source.yaml import load_yaml_mapping
from aiqa_data.domain import (
    SourceDatasetIdentity,
    SourceIntegrityReport,
    SourceLicenseReference,
    VerifiedSourceFile,
)


class ManifestDataset(BaseModel):
    """Validate versioned metadata that identifies the official dataset source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    challenge: str
    version: str
    subset: str
    homepage: str
    retrieved_on: date

    def to_domain(self) -> SourceDatasetIdentity:
        """Convert manifest dataset metadata to a framework-neutral value."""
        return SourceDatasetIdentity(
            name=self.name,
            challenge=self.challenge,
            version=self.version,
            subset=self.subset,
            homepage=self.homepage,
            retrieved_on=self.retrieved_on,
        )


class ManifestLicense(BaseModel):
    """Validate the license reference retained with the downloaded source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    identifier: str
    url: str

    def to_domain(self) -> SourceLicenseReference:
        """Convert manifest license metadata to a framework-neutral value."""
        return SourceLicenseReference(
            name=self.name,
            identifier=self.identifier,
            url=self.url,
        )


class ManifestCitation(BaseModel):
    """Validate the citation reference retained with the downloaded source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    doi: str


class ManifestFile(BaseModel):
    """Validate one immutable file expected from the official source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    source_url: str
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class SourceManifest(BaseModel):
    """Validate the complete source-manifest document before file operations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    dataset: ManifestDataset
    license: ManifestLicense
    citation: ManifestCitation
    files: tuple[ManifestFile, ...] = Field(min_length=1)


SourceFetcher = Callable[[str], bytes]


def load_source_manifest(path: Path) -> SourceManifest:
    """Load one versioned source-manifest document."""
    return SourceManifest.model_validate(load_yaml_mapping(path))


def acquire_source_manifest(
    path: Path,
    *,
    fetch: SourceFetcher | None = None,
) -> tuple[Path, ...]:
    """Download missing official files and verify them before publication."""
    document = load_source_manifest(path)
    root = path.parent
    root.mkdir(parents=True, exist_ok=True)
    fetch_source = fetch or download_bytes
    acquired: list[Path] = []
    for item in document.files:
        destination = root / item.path
        if matches_expected_file(
            destination,
            size_bytes=item.size_bytes,
            sha256=item.sha256,
        ):
            acquired.append(destination)
            continue
        payload = fetch_source(item.source_url)
        if len(payload) != item.size_bytes:
            raise ValueError(f"downloaded source size mismatch: {item.path}")
        if sha256_bytes(payload) != item.sha256:
            raise ValueError(f"downloaded source checksum mismatch: {item.path}")
        temporary = destination.with_name(f".{destination.name}.part")
        temporary.write_bytes(payload)
        temporary.replace(destination)
        acquired.append(destination)
    return tuple(acquired)


def verify_source_manifest(path: Path) -> SourceIntegrityReport:
    """Verify local source files and return typed source-integrity evidence."""
    document = load_source_manifest(path)
    root = path.parent
    verified: list[VerifiedSourceFile] = []
    for item in document.files:
        file_path = root / item.path
        if not file_path.is_file():
            raise ValueError(f"source file missing: {file_path}")
        actual_size = file_path.stat().st_size
        actual_hash = sha256_file(file_path)
        if actual_size != item.size_bytes:
            raise ValueError(f"source size mismatch: {item.path}")
        if actual_hash != item.sha256:
            raise ValueError(f"source checksum mismatch: {item.path}")
        verified.append(
            VerifiedSourceFile(
                path=str(item.path),
                size_bytes=actual_size,
                sha256=actual_hash,
            )
        )
    if not (root / "LICENSE.txt").is_file():
        raise ValueError("source license notice is missing")
    return SourceIntegrityReport(
        schema_version=1,
        dataset=document.dataset.to_domain(),
        license=document.license.to_domain(),
        files=tuple(verified),
    )
