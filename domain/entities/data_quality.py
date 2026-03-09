from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DataQualityRule:
    """A configurable data quality rule for Oracle EBS module validation."""

    rule_id: str
    rule_name: str
    module: str  # "GL", "AP", "HCM", "ALL"
    severity: str  # "ERROR", "WARNING", "INFO"
    rule_type: str  # "not_null", "range", "referential", "custom_sql", "balance", "uniqueness"
    table_name: str
    column_name: Optional[str] = None
    expression: Optional[str] = None  # SQL expression or Python lambda string
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    reference_table: Optional[str] = None
    reference_column: Optional[str] = None
    description: str = ""


@dataclass(frozen=True)
class DataQualityResult:
    """Outcome of evaluating a single data quality rule."""

    rule: DataQualityRule
    passed: bool
    violations_count: int = 0
    sample_violations: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_seconds: float = 0.0
    message: str = ""


@dataclass(frozen=True)
class DataQualityReport:
    """Aggregate report for all data quality rules evaluated against a module."""

    module: str
    rules_evaluated: int
    rules_passed: int
    rules_failed: int
    rules_warned: int
    results: List[DataQualityResult] = field(default_factory=list)
    executed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def pass_rate(self) -> float:
        return (
            self.rules_passed / self.rules_evaluated
            if self.rules_evaluated > 0
            else 0.0
        )

    @property
    def has_errors(self) -> bool:
        return any(
            not r.passed and r.rule.severity == "ERROR" for r in self.results
        )
