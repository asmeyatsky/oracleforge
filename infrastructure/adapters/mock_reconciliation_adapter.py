import logging
from typing import List
from decimal import Decimal
from domain.ports.reconciliation_ports import ReconciliationPort
from domain.value_objects.common import MultiOrgContext

logger = logging.getLogger(__name__)


class MockReconciliationAdapter(ReconciliationPort):
    """Mock reconciliation adapter returning matching source/target data.

    Simulates a successful reconciliation for demo and testing purposes.
    Configurable to simulate mismatches for failure testing.
    """

    def __init__(self, simulate_mismatch: bool = False):
        self.simulate_mismatch = simulate_mismatch

    async def get_source_row_count(self, table: str, context: MultiOrgContext) -> int:
        logger.info(f"MOCK: Counting source rows in {table}")
        counts = {
            "GL_JE_HEADERS": 15234,
            "GL_JE_LINES": 89102,
            "GL_BALANCES": 3450,
            "AP_INVOICES_ALL": 32100,
            "AP_INVOICE_LINES_ALL": 87650,
            "PER_ALL_PEOPLE_F": 9500,
        }
        return counts.get(table, 1000)

    async def get_target_row_count(self, dataset: str, table: str) -> int:
        logger.info(f"MOCK: Counting target rows in {dataset}.{table}")
        source_counts = {
            "gl_je_headers": 15234,
            "gl_je_lines": 89102,
            "gl_balances": 3450,
            "ap_invoices": 32100,
            "ap_invoice_lines": 87650,
            "per_all_people_f": 9500,
        }
        count = source_counts.get(table, 1000)
        if self.simulate_mismatch:
            count -= 2  # Simulate a small mismatch
        return count

    async def get_source_checksum(
        self, table: str, columns: List[str], context: MultiOrgContext
    ) -> str:
        logger.info(f"MOCK: Computing source checksum on {table}")
        return "MOCK_CHECKSUM_ABC123"

    async def get_target_checksum(
        self, dataset: str, table: str, columns: List[str]
    ) -> str:
        logger.info(f"MOCK: Computing target checksum on {dataset}.{table}")
        if self.simulate_mismatch:
            return "MOCK_CHECKSUM_XYZ789"
        return "MOCK_CHECKSUM_ABC123"

    async def get_source_aggregate(
        self, table: str, column: str, context: MultiOrgContext
    ) -> Decimal:
        logger.info(f"MOCK: Aggregating source {table}.{column}")
        aggregates = {
            ("GL_JE_LINES", "ACCOUNTED_DR"): Decimal("45678901.23"),
            ("GL_JE_LINES", "ACCOUNTED_CR"): Decimal("45678901.23"),
            ("AP_INVOICES_ALL", "INVOICE_AMOUNT"): Decimal("12345678.90"),
            ("AP_INVOICES_ALL", "AMOUNT_PAID"): Decimal("9876543.21"),
        }
        return aggregates.get((table, column), Decimal("1000000.00"))

    async def get_target_aggregate(
        self, dataset: str, table: str, column: str
    ) -> Decimal:
        logger.info(f"MOCK: Aggregating target {dataset}.{table}.{column}")
        # Map BQ table names back to Oracle table names
        bq_to_oracle = {
            "gl_je_lines": "GL_JE_LINES",
            "ap_invoices": "AP_INVOICES_ALL",
        }
        oracle_table = bq_to_oracle.get(table, table.upper())
        aggregates = {
            ("GL_JE_LINES", "accounted_dr"): Decimal("45678901.23"),
            ("GL_JE_LINES", "accounted_cr"): Decimal("45678901.23"),
            ("AP_INVOICES_ALL", "invoice_amount"): Decimal("12345678.90"),
            ("AP_INVOICES_ALL", "amount_paid"): Decimal("9876543.21"),
        }
        val = aggregates.get((oracle_table, column), Decimal("1000000.00"))
        if self.simulate_mismatch:
            val -= Decimal("100.00")
        return val
