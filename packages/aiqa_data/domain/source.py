"""Source-lineage values produced by raw data integrity verification."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SourceDatasetIdentity:
    """Stable identity and provenance metadata for one official source dataset."""

    name: str
    challenge: str
    version: str
    subset: str
    homepage: str
    retrieved_on: date

    def __post_init__(self) -> None:
        if not all(
            value and value.strip() == value
            for value in (
                self.name,
                self.challenge,
                self.version,
                self.subset,
                self.homepage,
            )
        ):
            raise ValueError(
                "source dataset identity fields must be non-empty and trimmed"
            )


@dataclass(frozen=True)
class SourceLicenseReference:
    """License reference retained with the downloaded source evidence."""

    name: str
    identifier: str
    url: str

    def __post_init__(self) -> None:
        if not all(
            value and value.strip() == value
            for value in (self.name, self.identifier, self.url)
        ):
            raise ValueError("source license fields must be non-empty and trimmed")


@dataclass(frozen=True)
class VerifiedSourceFile:
    """One source file whose local content matches the versioned manifest."""

    path: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        if not self.path or self.path.strip() != self.path:
            raise ValueError("verified source path must be non-empty and trimmed")
        if self.size_bytes < 1:
            raise ValueError("verified source size must be positive")
        if len(self.sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.sha256
        ):
            raise ValueError("verified source SHA-256 must be lowercase hexadecimal")


@dataclass(frozen=True)
class SourceIntegrityReport:
    """Typed evidence that every expected official source file was verified."""

    schema_version: int
    dataset: SourceDatasetIdentity
    license: SourceLicenseReference
    files: tuple[VerifiedSourceFile, ...]

    def __post_init__(self) -> None:
        if self.schema_version < 1:
            raise ValueError("source integrity schema version must be positive")
        if not self.files:
            raise ValueError("source integrity report requires verified files")
        paths = tuple(item.path for item in self.files)
        if len(paths) != len(set(paths)):
            raise ValueError("source integrity report file paths must be unique")
