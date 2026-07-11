"""Quality issue tracing domain objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IssueCandidate:
    """One possible cause of an operational quality issue."""

    category: str
    evidence: str
    owner: str
    audit_reference: str
    next_action: str


@dataclass(frozen=True)
class IssueTraceReport:
    """Prioritized issue trace report."""

    candidates: tuple[IssueCandidate, ...]

    @property
    def has_candidates(self) -> bool:
        """Return whether there are candidates to review."""
        return bool(self.candidates)
