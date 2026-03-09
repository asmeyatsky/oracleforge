"""CDC (Change Data Capture) domain entities.

Immutable value objects representing CDC stream configuration,
runtime status, and individual change events.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass(frozen=True)
class CDCStreamConfig:
    """Configuration for a CDC replication stream from Oracle to BigQuery."""
    stream_name: str
    source_schema: str  # Oracle schema
    source_tables: List[str]  # Tables to replicate
    target_dataset: str  # BigQuery target dataset
    target_project: str
    replication_mode: str = "continuous"  # "continuous", "snapshot", "incremental"
    backfill: bool = True


@dataclass(frozen=True)
class CDCStreamStatus:
    """Runtime status of a CDC stream."""
    stream_name: str
    status: str  # "RUNNING", "PAUSED", "FAILED", "NOT_STARTED", "DRAINING"
    tables_synced: int = 0
    total_tables: int = 0
    last_sync_time: Optional[datetime] = None
    rows_synced: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CDCEvent:
    """A single CDC change event captured from a stream."""
    stream_name: str
    table_name: str
    operation: str  # "INSERT", "UPDATE", "DELETE"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    row_count: int = 1
