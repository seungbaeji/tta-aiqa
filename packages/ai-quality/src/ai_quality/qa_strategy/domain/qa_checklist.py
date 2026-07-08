"""Final QA checklist domain objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QAChecklistItem:
    """One checklist item."""

    section: str
    text: str
    done: bool = False
    status: str = "unchecked"
    evidence: str = "-"
    qa_comment: str = ""
    owner: str = "-"
    next_action: str = "-"


@dataclass(frozen=True)
class QAChecklist:
    """Final checklist artifact."""

    items: tuple[QAChecklistItem, ...]

    @property
    def completion_rate(self) -> float:
        """Return evidence review completion ratio."""
        if not self.items:
            return 0.0
        done_count = sum(1 for item in self.items if item.done)
        return done_count / len(self.items)

    @property
    def blocking_statuses(self) -> tuple[str, ...]:
        """Return statuses that still block release approval."""
        blocking = {
            item.status
            for item in self.items
            if item.status in {"fail", "unverified", "hold"}
        }
        return tuple(sorted(blocking))

    @property
    def release_ready(self) -> bool:
        """Return whether the checklist has no blocking release status."""
        return not self.blocking_statuses
