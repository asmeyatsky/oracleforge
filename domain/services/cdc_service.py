"""CDC Orchestration domain service.

Contains pure business logic for building stream configurations from module
definitions, validating configs, and assessing stream health. No infrastructure
dependencies.
"""

from typing import Dict, List

from domain.entities.cdc import CDCStreamConfig, CDCStreamStatus


# Tables eligible for CDC replication, keyed by EBS module.
MODULE_CDC_TABLES: Dict[str, List[str]] = {
    "GL": [
        "GL_JE_HEADERS",
        "GL_JE_LINES",
        "GL_BALANCES",
        "GL_CODE_COMBINATIONS",
        "GL_PERIODS",
    ],
    "AP": [
        "AP_INVOICES_ALL",
        "AP_INVOICE_LINES_ALL",
        "AP_INVOICE_DISTRIBUTIONS_ALL",
        "AP_SUPPLIERS",
        "AP_SUPPLIER_SITES_ALL",
        "AP_CHECKS_ALL",
    ],
    "HCM": [
        "PER_ALL_PEOPLE_F",
        "PER_ALL_ASSIGNMENTS_F",
        "PAY_PAYROLL_ACTIONS",
        "PER_ADDRESSES_F",
    ],
}

VALID_REPLICATION_MODES = {"continuous", "snapshot", "incremental"}


class CDCOrchestrationService:
    """Orchestrates CDC streams, builds configs from module definitions, monitors health."""

    def build_stream_config(
        self,
        module: str,
        source_schema: str,
        target_dataset: str,
        target_project: str,
    ) -> CDCStreamConfig:
        """Build a CDCStreamConfig for a given module using the canonical table list.

        Raises ValueError if the module is unknown.
        """
        module_upper = module.upper()
        tables = MODULE_CDC_TABLES.get(module_upper)
        if tables is None:
            raise ValueError(f"Unknown module: {module}")

        stream_name = f"cdc-{module_upper.lower()}-{source_schema.lower()}"
        return CDCStreamConfig(
            stream_name=stream_name,
            source_schema=source_schema,
            source_tables=list(tables),
            target_dataset=target_dataset,
            target_project=target_project,
        )

    def validate_stream_config(self, config: CDCStreamConfig) -> List[str]:
        """Validate a CDCStreamConfig and return a list of error messages (empty = valid)."""
        errors: List[str] = []

        if not config.stream_name or not config.stream_name.strip():
            errors.append("stream_name is required")
        if not config.source_schema or not config.source_schema.strip():
            errors.append("source_schema is required")
        if not config.source_tables:
            errors.append("source_tables must not be empty")
        if not config.target_dataset or not config.target_dataset.strip():
            errors.append("target_dataset is required")
        if not config.target_project or not config.target_project.strip():
            errors.append("target_project is required")
        if config.replication_mode not in VALID_REPLICATION_MODES:
            errors.append(
                f"replication_mode must be one of {sorted(VALID_REPLICATION_MODES)}, "
                f"got '{config.replication_mode}'"
            )

        return errors

    def is_stream_healthy(self, status: CDCStreamStatus) -> bool:
        """Return True if the stream is considered healthy.

        Healthy means: status is RUNNING, no errors, and some tables are synced.
        """
        return (
            status.status == "RUNNING"
            and len(status.errors) == 0
            and status.tables_synced > 0
        )

    def calculate_sync_progress(self, status: CDCStreamStatus) -> float:
        """Calculate sync progress as a float from 0.0 to 1.0.

        Returns 0.0 if total_tables is zero (no tables configured).
        """
        if status.total_tables <= 0:
            return 0.0
        return min(status.tables_synced / status.total_tables, 1.0)
