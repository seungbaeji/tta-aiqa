"""PhysioNet source contract, manifest, and integrity adapters."""

from __future__ import annotations

import hashlib
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import yaml
from pydantic import BaseModel, ConfigDict, Field

from aiqa_data.adapters.split import StratifiedSplitConfig


@dataclass(frozen=True)
class PhysioNetSourceConfig:
    source_manifest_path: Path
    records_dir: Path
    outcomes_path: Path
    expected_record_count: int
    expected_death_count: int
    target_column: str
    blocked_outcome_columns: tuple[str, ...]
    observation_window_hours: int


class PhysioNetSourceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    dataset: str = Field(min_length=1)
    source_manifest_path: Path
    records_dir: Path
    outcomes_path: Path
    expected_record_count: int = Field(gt=0)
    expected_death_count: int = Field(gt=0)
    record_columns: tuple[str, str, str]
    record_id_parameter: str
    target_column: str
    blocked_outcome_columns: tuple[str, ...]
    observation_window_hours: int = Field(gt=0)

    def to_config(self) -> PhysioNetSourceConfig:
        if self.record_columns != ("Time", "Parameter", "Value"):
            raise ValueError("unsupported PhysioNet record columns")
        if self.record_id_parameter != "RecordID":
            raise ValueError("unsupported PhysioNet record identifier")
        return PhysioNetSourceConfig(
            source_manifest_path=self.source_manifest_path,
            records_dir=self.records_dir,
            outcomes_path=self.outcomes_path,
            expected_record_count=self.expected_record_count,
            expected_death_count=self.expected_death_count,
            target_column=self.target_column,
            blocked_outcome_columns=self.blocked_outcome_columns,
            observation_window_hours=self.observation_window_hours,
        )


class SplitParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    random_seed: int
    train_ratio: float = Field(gt=0, lt=1)
    valid_ratio: float = Field(gt=0, lt=1)
    test_ratio: float = Field(gt=0, lt=1)
    operational_ratio: float = Field(gt=0, lt=1)


class ParametersDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    data: SplitParameters


class ManifestDataset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    challenge: str
    version: str
    subset: str
    homepage: str
    retrieved_on: date


class ManifestLicense(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    identifier: str
    url: str


class ManifestCitation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    doi: str


class ManifestFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    source_url: str
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class SourceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    dataset: ManifestDataset
    license: ManifestLicense
    citation: ManifestCitation
    files: tuple[ManifestFile, ...] = Field(min_length=1)


SourceFetcher = Callable[[str], bytes]


def load_source_contract(path: Path) -> PhysioNetSourceConfig:
    return PhysioNetSourceDocument.model_validate(_yaml_mapping(path)).to_config()


def load_split_config(path: Path) -> StratifiedSplitConfig:
    document = ParametersDocument.model_validate(_yaml_mapping(path))
    return StratifiedSplitConfig(**document.data.model_dump())


def acquire_source_manifest(
    path: Path, *, fetch: SourceFetcher | None = None
) -> tuple[Path, ...]:
    """Download missing official files and verify them before publication."""
    document = SourceManifest.model_validate(_yaml_mapping(path))
    root = path.parent
    root.mkdir(parents=True, exist_ok=True)
    fetch_source = fetch or _fetch_bytes
    acquired: list[Path] = []
    for item in document.files:
        destination = root / item.path
        if _matches_manifest(destination, item):
            acquired.append(destination)
            continue
        payload = fetch_source(item.source_url)
        if len(payload) != item.size_bytes:
            raise ValueError(f"downloaded source size mismatch: {item.path}")
        if hashlib.sha256(payload).hexdigest() != item.sha256:
            raise ValueError(f"downloaded source checksum mismatch: {item.path}")
        temporary = destination.with_name(f".{destination.name}.part")
        temporary.write_bytes(payload)
        temporary.replace(destination)
        acquired.append(destination)
    return tuple(acquired)


def verify_source_manifest(path: Path) -> dict[str, object]:
    document = SourceManifest.model_validate(_yaml_mapping(path))
    root = path.parent
    verified: list[dict[str, object]] = []
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
            {"path": str(item.path), "size_bytes": actual_size, "sha256": actual_hash}
        )
    if not (root / "LICENSE.txt").is_file():
        raise ValueError("source license notice is missing")
    return {
        "schema_version": 1,
        "dataset": document.dataset.model_dump(mode="json"),
        "license": document.license.model_dump(),
        "files": verified,
        "verified": True,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _matches_manifest(path: Path, item: ManifestFile) -> bool:
    return (
        path.is_file()
        and path.stat().st_size == item.size_bytes
        and sha256_file(path) == item.sha256
    )


def _fetch_bytes(url: str) -> bytes:
    with urlopen(url, timeout=60) as response:  # noqa: S310 - versioned data URL
        return response.read()


def extract_archive(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        if not members or any(
            Path(member.filename).is_absolute() or ".." in Path(member.filename).parts
            for member in members
        ):
            raise ValueError("archive contains an unsafe member path")
        archive.extractall(destination)


def _yaml_mapping(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        payload = yaml.safe_load(file)
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload
