"""Build backend wrapper for normal and JupyterLite package variants."""

from __future__ import annotations

import base64
import hashlib
import os
import zipfile
from pathlib import Path
from typing import Any

from hatchling import build as hatchling_build

FULL_DISTRIBUTION = "ttamlops-ai-quality"
LITE_DISTRIBUTION = "ttamlops-ai-quality-lite"
VERSION = "0.1.0"
LITE_WHEEL = "ttamlops_ai_quality_lite-0.1.0-py3-none-any.whl"


def _is_lite(config_settings: dict[str, Any] | None) -> bool:
    if not config_settings:
        return False
    value = config_settings.get("ai-quality.variant")
    if isinstance(value, list):
        value = value[-1] if value else None
    return str(value).lower() == "lite"


def _hash_record(data: bytes) -> tuple[str, int]:
    digest = hashlib.sha256(data).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"sha256={encoded}", len(data)


def build_lite_wheel(wheel_directory: str) -> str:
    project_root = Path(__file__).resolve().parents[1]
    wheel_path = Path(wheel_directory) / LITE_WHEEL
    wheel_path.parent.mkdir(parents=True, exist_ok=True)

    files: dict[str, bytes] = {
        "ai_quality/__init__.py": (
            project_root / "src" / "ai_quality" / "__init__.py"
        ).read_bytes(),
        "ai_quality/lite.py": (
            project_root / "src" / "ai_quality" / "lite.py"
        ).read_bytes(),
        "ttamlops_ai_quality_lite-0.1.0.dist-info/METADATA": "\n".join(
            [
                "Metadata-Version: 2.1",
                f"Name: {LITE_DISTRIBUTION}",
                f"Version: {VERSION}",
                "Summary: Browser-safe helpers for TTA AI QA JupyterLite labs.",
                "Requires-Python: >=3.11",
                "Requires-Dist: numpy>=1.26,<2.3",
                "Requires-Dist: pandas>=2.2",
                "",
            ]
        ).encode(),
        "ttamlops_ai_quality_lite-0.1.0.dist-info/WHEEL": "\n".join(
            [
                "Wheel-Version: 1.0",
                "Generator: packages/ai-quality/build_backend/ai_quality_build.py",
                "Root-Is-Purelib: true",
                "Tag: py3-none-any",
                "",
            ]
        ).encode(),
    }

    record_path = "ttamlops_ai_quality_lite-0.1.0.dist-info/RECORD"
    record_rows = []
    for archive_path, data in files.items():
        digest, size = _hash_record(data)
        record_rows.append(f"{archive_path},{digest},{size}")
    record_rows.append(f"{record_path},,")
    files[record_path] = ("\n".join(record_rows) + "\n").encode()

    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for archive_path, data in files.items():
            archive.writestr(archive_path, data)

    return wheel_path.name


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    if _is_lite(config_settings):
        return build_lite_wheel(wheel_directory)
    return hatchling_build.build_wheel(
        wheel_directory,
        config_settings=config_settings,
        metadata_directory=metadata_directory,
    )


def build_sdist(
    sdist_directory: str, config_settings: dict[str, Any] | None = None
) -> str:
    return hatchling_build.build_sdist(sdist_directory, config_settings=config_settings)


def build_editable(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    return hatchling_build.build_editable(
        wheel_directory,
        config_settings=config_settings,
        metadata_directory=metadata_directory,
    )


def get_requires_for_build_wheel(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    return hatchling_build.get_requires_for_build_wheel(config_settings=config_settings)


def get_requires_for_build_sdist(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    return hatchling_build.get_requires_for_build_sdist(config_settings=config_settings)


def get_requires_for_build_editable(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    return hatchling_build.get_requires_for_build_editable(
        config_settings=config_settings
    )


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    if _is_lite(config_settings):
        dist_info = (
            Path(metadata_directory) / "ttamlops_ai_quality_lite-0.1.0.dist-info"
        )
        dist_info.mkdir(parents=True, exist_ok=True)
        (dist_info / "METADATA").write_text(
            "\n".join(
                [
                    "Metadata-Version: 2.1",
                    f"Name: {LITE_DISTRIBUTION}",
                    f"Version: {VERSION}",
                    "Summary: Browser-safe helpers for TTA AI QA JupyterLite labs.",
                    "Requires-Python: >=3.11",
                    "Requires-Dist: numpy>=1.26,<2.3",
                    "Requires-Dist: pandas>=2.2",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (dist_info / "WHEEL").write_text(
            "\n".join(
                [
                    "Wheel-Version: 1.0",
                    "Generator: packages/ai-quality/build_backend/ai_quality_build.py",
                    "Root-Is-Purelib: true",
                    "Tag: py3-none-any",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return os.fspath(dist_info.name)
    return hatchling_build.prepare_metadata_for_build_wheel(
        metadata_directory,
        config_settings=config_settings,
    )
