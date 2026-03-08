"""Domain events for the migration pipeline.

Events are immutable records of things that happened during a migration.
They carry context for observability, auditing, and downstream reactions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any


@dataclass(frozen=True)
class MigrationEvent:
    """Base class for all migration domain events."""
    event_id: str
    module: str
    period_name: str
    org_id: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class MigrationStartedEvent(MigrationEvent):
    """Emitted when a migration pipeline begins."""
    tables: List[str] = field(default_factory=list)
    dry_run: bool = False


@dataclass(frozen=True)
class ExtractionCompleteEvent(MigrationEvent):
    """Emitted when data extraction from Oracle finishes."""
    rows_extracted: int = 0
    tables_extracted: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class TransformationCompleteEvent(MigrationEvent):
    """Emitted when entity resolution and transformation finishes."""
    entities_resolved: int = 0
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class ComplianceCheckEvent(MigrationEvent):
    """Emitted after compliance checks (PDPL/NDMO/SAMA) run."""
    standard: str = ""
    passed: bool = True
    pii_columns_found: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class LoadCompleteEvent(MigrationEvent):
    """Emitted when data loading to BigQuery completes."""
    layer: str = ""  # "bronze", "silver", "gold"
    dataset: str = ""
    rows_loaded: int = 0
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class ReconciliationCompleteEvent(MigrationEvent):
    """Emitted after reconciliation checks run."""
    passed: bool = True
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    certificate_id: Optional[str] = None


@dataclass(frozen=True)
class MigrationCompleteEvent(MigrationEvent):
    """Emitted when the entire migration pipeline finishes."""
    success: bool = True
    total_rows: int = 0
    total_duration_seconds: float = 0.0
    certificate_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
