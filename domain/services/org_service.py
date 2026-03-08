import logging
from typing import List, Dict, Any, Optional
from domain.ports.oracle_ports import OracleSourcePort
from domain.value_objects.common import MultiOrgContext

logger = logging.getLogger(__name__)

class MultiOrgResolver:
    """Service for resolving Oracle EBS/Fusion multi-org structures."""

    def __init__(self, oracle_port: OracleSourcePort):
        self.oracle_port = oracle_port

    async def resolve_org_id(self, org_name: str) -> Optional[int]:
        """Fetch org_id for a given organization name."""
        logger.info(f"Resolving org_id for organization: {org_name}")
        query = f"SELECT organization_id FROM hr_all_organization_units WHERE name = '{org_name}'"
        result = await self.oracle_port.execute_query(query)
        return result[0]["organization_id"] if result else None

    async def get_org_context(self, org_id: int) -> Optional[MultiOrgContext]:
        """Fetch MultiOrgContext (org_id, ledger_id, SOB ID) for a given org_id."""
        logger.info(f"Fetching org context for org_id: {org_id}")
        # Simplified query to mock data
        query = f"SELECT set_of_books_id, ledger_id FROM hr_operating_units WHERE organization_id = {org_id}"
        result = await self.oracle_port.execute_query(query)
        if result:
            return MultiOrgContext(
                org_id=org_id,
                set_of_books_id=result[0]["set_of_books_id"],
                ledger_id=result[0]["ledger_id"]
            )
        return None
