from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from decimal import Decimal
from domain.value_objects.common import Money, MultiOrgContext, Period


@dataclass(frozen=True)
class ReconciliationCheck:
    """A single reconciliation check result (row count, checksum, or balance)."""
    check_type: str  # "row_count", "checksum", "aggregate_balance"
    source_label: str  # e.g., "Oracle GL_JE_HEADERS"
    target_label: str  # e.g., "BigQuery gold.gl_journals"
    source_value: Decimal
    target_value: Decimal
    tolerance: Decimal = Decimal("0.01")

    @property
    def variance(self) -> Decimal:
        return abs(self.source_value - self.target_value)

    @property
    def is_within_tolerance(self) -> bool:
        return self.variance <= self.tolerance

    @property
    def variance_pct(self) -> Decimal:
        if self.source_value == Decimal("0"):
            return Decimal("0") if self.target_value == Decimal("0") else Decimal("100")
        return (self.variance / abs(self.source_value)) * Decimal("100")


@dataclass(frozen=True)
class ReconciliationResult:
    """Complete reconciliation result for one migration run."""
    module: str  # "GL", "AP", "HCM"
    period: Period
    context: MultiOrgContext
    checks: List[ReconciliationCheck]
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def passed(self) -> bool:
        return all(check.is_within_tolerance for check in self.checks)

    @property
    def failed_checks(self) -> List[ReconciliationCheck]:
        return [c for c in self.checks if not c.is_within_tolerance]

    @property
    def total_checks(self) -> int:
        return len(self.checks)

    @property
    def passed_checks_count(self) -> int:
        return sum(1 for c in self.checks if c.is_within_tolerance)


@dataclass(frozen=True)
class CertificateOfAccuracy:
    """Audit-ready certificate generated after reconciliation passes."""
    certificate_id: str
    module: str
    period: Period
    context: MultiOrgContext
    result: ReconciliationResult
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    issuer: str = "OracleForge Reconciliation Engine v1.0"

    @property
    def status(self) -> str:
        return "CERTIFIED" if self.result.passed else "FAILED"

    @property
    def summary(self) -> str:
        return (
            f"Certificate {self.certificate_id}: {self.module} {self.period.period_name} — "
            f"{self.result.passed_checks_count}/{self.result.total_checks} checks passed — "
            f"Status: {self.status}"
        )
