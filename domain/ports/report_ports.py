"""Port definitions for report generation (Clean Architecture boundary).

These protocols define the contract for generating audit-ready documents
from domain entities. Infrastructure adapters implement the actual file creation.
"""

from typing import Protocol, List

from domain.entities.reconciliation import CertificateOfAccuracy

# Import at TYPE_CHECKING level to avoid circular deps; runtime uses duck typing.
try:
    from application.use_cases.migration_pipeline import MigrationResult
except ImportError:  # pragma: no cover — allows domain layer to remain independent
    MigrationResult = object  # type: ignore[assignment,misc]


class ReportGeneratorPort(Protocol):
    """Port for producing audit-ready reports from domain entities."""

    async def generate_certificate_report(
        self, certificate: CertificateOfAccuracy, output_path: str
    ) -> str:
        """Generate an audit-ready report from a certificate. Returns the file path."""
        ...

    async def generate_migration_summary(
        self, results: List, output_path: str  # List[MigrationResult]
    ) -> str:
        """Generate a summary report for multiple migration runs."""
        ...
