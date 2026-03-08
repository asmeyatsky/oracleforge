import logging
from typing import List, Dict, Any, Optional
from domain.ports.oracle_ports import OracleSourcePort
from domain.entities.gl import JournalEntry, GLBalance
from domain.entities.ap import Invoice
from domain.entities.hcm import Employee
from domain.value_objects.common import Period, MultiOrgContext

logger = logging.getLogger(__name__)

class MockOracleAdapter(OracleSourcePort):
    """Mock implementation of OracleSourcePort for local testing."""

    async def get_gl_journals(self, period: Period, ledger_id: int) -> List[JournalEntry]:
        logger.info(f"MOCK: Fetching GL journals for period {period.period_name}")
        return []

    async def get_gl_balances(self, period: Period, ledger_id: int) -> List[GLBalance]:
        logger.info(f"MOCK: Fetching GL balances for period {period.period_name}")
        return []

    async def get_ap_invoices(self, context: MultiOrgContext) -> List[Invoice]:
        logger.info(f"MOCK: Fetching AP invoices for org {context.org_id}")
        return []

    async def get_hcm_employees(self) -> List[Employee]:
        logger.info("MOCK: Fetching HCM employees")
        return []

    async def get_schema_metadata(self) -> Dict[str, Any]:
        logger.info("MOCK: Fetching schema metadata")
        return {
            "tables": [
                {"name": "GL_JE_HEADERS", "module": "GL", "classification": "transactional"},
                {"name": "AP_INVOICES_ALL", "module": "AP", "classification": "transactional"},
                {"name": "PER_ALL_PEOPLE_F", "module": "HCM", "classification": "master_data"}
            ]
        }

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        logger.info(f"MOCK: Executing query: {query}")
        return []
