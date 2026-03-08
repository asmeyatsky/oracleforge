from typing import Protocol, List, Dict, Any, Optional
from domain.entities.gl import JournalEntry, GLBalance, ChartOfAccounts
from domain.entities.ap import Invoice, Payment, Supplier
from domain.entities.hcm import Employee, Assignment, PayrollSummary
from domain.value_objects.common import Period, MultiOrgContext

class OracleSourcePort(Protocol):
    """Port for interrogating and extracting data from Oracle EBS or Fusion Cloud."""

    async def get_gl_journals(self, period: Period, ledger_id: int) -> List[JournalEntry]:
        """Fetch GL journals for a given period and ledger."""
        ...

    async def get_gl_balances(self, period: Period, ledger_id: int) -> List[GLBalance]:
        """Fetch GL balances for a given period and ledger."""
        ...

    async def get_ap_invoices(self, context: MultiOrgContext) -> List[Invoice]:
        """Fetch AP invoices for a given multi-org context."""
        ...

    async def get_hcm_employees(self) -> List[Employee]:
        """Fetch HCM employees."""
        ...

    async def get_schema_metadata(self) -> Dict[str, Any]:
        """Fetch table metadata, column definitions, and relationships."""
        ...

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a raw SQL query against the Oracle source."""
        ...
