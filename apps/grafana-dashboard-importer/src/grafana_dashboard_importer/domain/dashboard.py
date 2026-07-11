"""Dashboard import values and invariants."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DashboardImport:
    dashboard: dict[str, Any]
    folder_uid: str

    def __post_init__(self) -> None:
        uid = self.dashboard.get("uid")
        title = self.dashboard.get("title")
        if not isinstance(uid, str) or not uid:
            raise ValueError("dashboard template requires a stable UID")
        if not isinstance(title, str) or not title:
            raise ValueError("dashboard template requires a title")
        if not self.folder_uid:
            raise ValueError("Grafana folder UID is required")


@dataclass(frozen=True)
class ImportResult:
    uid: str
    url: str
    status: str
