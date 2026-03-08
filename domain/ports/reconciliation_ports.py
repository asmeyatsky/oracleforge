from typing import Protocol, List, Dict, Any
from decimal import Decimal
from domain.value_objects.common import Period, MultiOrgContext


class ReconciliationPort(Protocol):
    """Port for comparing source (Oracle) and target (BigQuery) data post-migration."""

    async def get_source_row_count(self, table: str, context: MultiOrgContext) -> int:
        """Get row count from source Oracle table."""
        ...

    async def get_target_row_count(self, dataset: str, table: str) -> int:
        """Get row count from target BigQuery table."""
        ...

    async def get_source_checksum(self, table: str, columns: List[str], context: MultiOrgContext) -> str:
        """Compute a checksum over specified columns in Oracle source."""
        ...

    async def get_target_checksum(self, dataset: str, table: str, columns: List[str]) -> str:
        """Compute a checksum over specified columns in BigQuery target."""
        ...

    async def get_source_aggregate(self, table: str, column: str, context: MultiOrgContext) -> Decimal:
        """Get aggregate sum of a numeric column from Oracle source."""
        ...

    async def get_target_aggregate(self, dataset: str, table: str, column: str) -> Decimal:
        """Get aggregate sum of a numeric column from BigQuery target."""
        ...
