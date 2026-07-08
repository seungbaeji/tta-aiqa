"""Release approval domain objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApprovalCriteria:
    """Release approval criteria."""

    minimum_precision: float
    minimum_recall: float
    maximum_error_rate: float
    maximum_latency_average_ms: float


@dataclass(frozen=True)
class ApprovalCheckResult:
    """Observed value compared with one release approval criterion."""

    name: str
    observed: float | bool | str
    criterion: str
    passed: bool


@dataclass(frozen=True)
class ApprovalRisk:
    """Unresolved release risk that blocks or qualifies approval."""

    area: str
    status: str
    evidence: str
    owner: str
    next_action: str


@dataclass(frozen=True)
class ReleaseRiskTradeoff:
    """Risk created by one release gate decision option."""

    decision: str
    company_risk: str
    evidence: str
    missing_evidence: str
    owner: str
    next_action: str


@dataclass(frozen=True)
class ApprovalDecision:
    """Approval or hold decision."""

    approved: bool
    failed_checks: tuple[str, ...]
    notes: tuple[str, ...]
    check_results: tuple[ApprovalCheckResult, ...] = ()
    unresolved_risks: tuple[ApprovalRisk, ...] = ()
    decision_summary: str = ""
    recommendation: str = ""
    risk_tradeoffs: tuple[ReleaseRiskTradeoff, ...] = ()
    re_evaluation_condition: str = ""
