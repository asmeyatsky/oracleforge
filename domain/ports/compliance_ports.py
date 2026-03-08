from typing import Protocol, List, Dict, Any, Optional

class CompliancePort(Protocol):
    """Port for managing regional compliance (SAMA, NDMO, PDPL, GDPR)."""

    async def identify_pii(self, dataset: str, table: str) -> List[str]:
        """Identify PII columns in a given BigQuery table."""
        ...

    async def apply_data_masking(self, table: str, columns: List[str]) -> bool:
        """Apply BigQuery dynamic data masking to sensitive columns."""
        ...

    async def log_consent_action(self, person_id: int, action: str, details: str) -> bool:
        """Log actions related to PDPL/GDPR data subject rights."""
        ...

    async def generate_compliance_report(self, standard: str) -> Dict[str, Any]:
        """Generate an automated audit report for a specific compliance standard."""
        ...
