"""Migration Pipeline Use Case — the core Extract → Resolve → Load → Reconcile → Certify flow.

Orchestrates the full migration of a module (GL, AP, HCM) from Oracle EBS to
BigQuery, including compliance checks, reconciliation, and certificate issuance.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from decimal import Decimal

from domain.ports.oracle_ports import OracleSourcePort
from domain.ports.gcp_ports import GCPTargetPort
from domain.ports.reconciliation_ports import ReconciliationPort
from domain.ports.event_ports import EventBusPort
from domain.services.reconciliation_service import ReconciliationService
from domain.services.entity_service import EntityResolutionService
from domain.value_objects.common import Period, MultiOrgContext
from domain.events.migration_events import (
    MigrationStartedEvent,
    ExtractionCompleteEvent,
    LoadCompleteEvent,
    ReconciliationCompleteEvent,
    MigrationCompleteEvent,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MigrationResult:
    """Complete result of a migration pipeline run."""
    module: str
    period: Period
    context: MultiOrgContext
    success: bool
    rows_extracted: int = 0
    rows_loaded: int = 0
    reconciliation_passed: bool = False
    certificate_id: Optional[str] = None
    certificate_status: Optional[str] = None
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    steps_completed: List[str] = field(default_factory=list)


# Table mappings for each module
MODULE_TABLES: Dict[str, Dict[str, str]] = {
    "GL": {
        "GL_JE_HEADERS": "gl_je_headers",
        "GL_JE_LINES": "gl_je_lines",
        "GL_BALANCES": "gl_balances",
        "GL_CODE_COMBINATIONS": "gl_code_combinations",
    },
    "AP": {
        "AP_INVOICES_ALL": "ap_invoices",
        "AP_INVOICE_LINES_ALL": "ap_invoice_lines",
        "AP_SUPPLIERS": "ap_suppliers",
    },
    "HCM": {
        "PER_ALL_PEOPLE_F": "per_all_people_f",
        "PAY_PAYROLL_ACTIONS": "pay_payroll_actions",
    },
}

# Reconciliation checks per module
MODULE_RECON_CHECKS: Dict[str, List[Dict[str, Any]]] = {
    "GL": [
        {"type": "row_count", "source_table": "GL_JE_HEADERS", "target_table": "gl_je_headers"},
        {"type": "row_count", "source_table": "GL_JE_LINES", "target_table": "gl_je_lines"},
        {"type": "aggregate", "source_table": "GL_JE_LINES", "target_table": "gl_je_lines",
         "source_col": "ACCOUNTED_DR", "target_col": "accounted_dr"},
        {"type": "aggregate", "source_table": "GL_JE_LINES", "target_table": "gl_je_lines",
         "source_col": "ACCOUNTED_CR", "target_col": "accounted_cr"},
    ],
    "AP": [
        {"type": "row_count", "source_table": "AP_INVOICES_ALL", "target_table": "ap_invoices"},
        {"type": "row_count", "source_table": "AP_INVOICE_LINES_ALL", "target_table": "ap_invoice_lines"},
        {"type": "aggregate", "source_table": "AP_INVOICES_ALL", "target_table": "ap_invoices",
         "source_col": "INVOICE_AMOUNT", "target_col": "invoice_amount"},
    ],
    "HCM": [
        {"type": "row_count", "source_table": "PER_ALL_PEOPLE_F", "target_table": "per_all_people_f"},
    ],
}


class MigrationPipelineUseCase:
    """Orchestrates the end-to-end migration pipeline.

    Pipeline steps:
    1. Extract data from Oracle via OracleSourcePort
    2. Resolve raw data into canonical domain entities
    3. Flatten entities to dicts for BigQuery loading
    4. Load to BigQuery Bronze layer via GCPTargetPort
    5. Run reconciliation checks via ReconciliationPort
    6. Issue Certificate of Accuracy
    7. Publish domain events throughout
    """

    def __init__(
        self,
        oracle_port: OracleSourcePort,
        gcp_port: GCPTargetPort,
        reconciliation_port: ReconciliationPort,
        event_bus: EventBusPort,
        bronze_dataset: str = "bronze",
    ):
        self.oracle_port = oracle_port
        self.gcp_port = gcp_port
        self.reconciliation_port = reconciliation_port
        self.event_bus = event_bus
        self.reconciliation_service = ReconciliationService()
        self.entity_service = EntityResolutionService()
        self.bronze_dataset = bronze_dataset

    async def execute(
        self,
        module: str,
        period: Period,
        context: MultiOrgContext,
        dry_run: bool = False,
    ) -> MigrationResult:
        """Execute the full migration pipeline for a module."""
        start_time = time.time()
        run_id = str(uuid.uuid4())[:8]
        module = module.upper()
        errors: List[str] = []
        steps_completed: List[str] = []
        total_rows = 0

        logger.info(f"[{run_id}] Starting {module} migration for {period.period_name} org={context.org_id}")

        # Publish start event
        await self.event_bus.publish(MigrationStartedEvent(
            event_id=run_id, module=module, period_name=period.period_name,
            org_id=context.org_id, tables=list(MODULE_TABLES.get(module, {}).keys()),
            dry_run=dry_run,
        ))

        # Step 1: Extract
        try:
            extracted_data = await self._extract(module, period, context)
            total_rows = sum(len(rows) for rows in extracted_data.values())
            steps_completed.append("extract")
            logger.info(f"[{run_id}] Extracted {total_rows} total rows from {len(extracted_data)} sources")

            await self.event_bus.publish(ExtractionCompleteEvent(
                event_id=run_id, module=module, period_name=period.period_name,
                org_id=context.org_id, rows_extracted=total_rows,
                tables_extracted=list(extracted_data.keys()),
            ))
        except Exception as e:
            errors.append(f"Extraction failed: {e}")
            logger.error(f"[{run_id}] Extraction failed: {e}")
            return self._build_result(module, period, context, False, errors=errors,
                                       steps=steps_completed, start_time=start_time)

        # Step 2: Load to Bronze (skip on dry run)
        rows_loaded = 0
        if not dry_run:
            try:
                rows_loaded = await self._load_bronze(module, extracted_data)
                steps_completed.append("load_bronze")
                logger.info(f"[{run_id}] Loaded {rows_loaded} rows to Bronze layer")

                await self.event_bus.publish(LoadCompleteEvent(
                    event_id=run_id, module=module, period_name=period.period_name,
                    org_id=context.org_id, layer="bronze", dataset=self.bronze_dataset,
                    rows_loaded=rows_loaded,
                ))
            except Exception as e:
                errors.append(f"Bronze load failed: {e}")
                logger.error(f"[{run_id}] Bronze load failed: {e}")
                return self._build_result(module, period, context, False, rows_extracted=total_rows,
                                           errors=errors, steps=steps_completed, start_time=start_time)
        else:
            steps_completed.append("load_bronze (dry_run)")
            rows_loaded = total_rows

        # Step 3: Reconciliation
        try:
            recon_result = await self._reconcile(module, context)
            steps_completed.append("reconcile")

            cert_id = f"CERT-{module}-{period.period_year}-{period.period_num:02d}-{run_id}"
            cert = self.reconciliation_service.issue_certificate(recon_result, cert_id)

            await self.event_bus.publish(ReconciliationCompleteEvent(
                event_id=run_id, module=module, period_name=period.period_name,
                org_id=context.org_id, passed=recon_result.passed,
                total_checks=recon_result.total_checks,
                passed_checks=recon_result.passed_checks_count,
                failed_checks=len(recon_result.failed_checks),
                certificate_id=cert_id,
            ))

            steps_completed.append("certify")
        except Exception as e:
            errors.append(f"Reconciliation failed: {e}")
            logger.error(f"[{run_id}] Reconciliation failed: {e}")
            return self._build_result(module, period, context, False, rows_extracted=total_rows,
                                       rows_loaded=rows_loaded, errors=errors,
                                       steps=steps_completed, start_time=start_time)

        # Step 4: Complete
        success = recon_result.passed
        duration = time.time() - start_time

        await self.event_bus.publish(MigrationCompleteEvent(
            event_id=run_id, module=module, period_name=period.period_name,
            org_id=context.org_id, success=success, total_rows=total_rows,
            total_duration_seconds=duration, certificate_id=cert_id,
        ))

        logger.info(f"[{run_id}] Migration complete: {cert.summary}")

        return MigrationResult(
            module=module, period=period, context=context, success=success,
            rows_extracted=total_rows, rows_loaded=rows_loaded,
            reconciliation_passed=recon_result.passed,
            certificate_id=cert_id, certificate_status=cert.status,
            duration_seconds=round(duration, 2),
            steps_completed=steps_completed,
        )

    async def _extract(self, module: str, period: Period, context: MultiOrgContext) -> Dict[str, List]:
        """Extract data from Oracle based on module type."""
        data: Dict[str, List] = {}

        if module == "GL":
            journals = await self.oracle_port.get_gl_journals(period, context.ledger_id or 2001)
            balances = await self.oracle_port.get_gl_balances(period, context.ledger_id or 2001)
            data["GL_JE_HEADERS"] = journals
            data["GL_BALANCES"] = balances
        elif module == "AP":
            invoices = await self.oracle_port.get_ap_invoices(context)
            data["AP_INVOICES_ALL"] = invoices
        elif module == "HCM":
            employees = await self.oracle_port.get_hcm_employees()
            data["PER_ALL_PEOPLE_F"] = employees

        return data

    async def _load_bronze(self, module: str, extracted_data: Dict[str, List]) -> int:
        """Flatten entities and load to BigQuery Bronze layer."""
        total_loaded = 0
        table_map = MODULE_TABLES.get(module, {})

        for source_table, entities in extracted_data.items():
            target_table = table_map.get(source_table, source_table.lower())
            # Flatten entities to dicts for BigQuery
            rows = self._flatten_entities(entities)
            if rows:
                await self.gcp_port.load_to_bigquery(self.bronze_dataset, target_table, rows)
                total_loaded += len(rows)

        return total_loaded

    def _flatten_entities(self, entities: List) -> List[Dict[str, Any]]:
        """Flatten domain entities to flat dictionaries for BigQuery loading."""
        rows = []
        for entity in entities:
            if hasattr(entity, '__dataclass_fields__'):
                row = {}
                for field_name, field_info in entity.__dataclass_fields__.items():
                    value = getattr(entity, field_name)
                    if hasattr(value, 'amount') and hasattr(value, 'currency'):
                        # Money value object
                        row[field_name] = float(value.amount)
                        row[f"{field_name}_currency"] = value.currency
                    elif hasattr(value, '__dataclass_fields__'):
                        # Nested dataclass — skip complex nesting for bronze
                        row[field_name] = str(value)
                    elif isinstance(value, list):
                        row[f"{field_name}_count"] = len(value)
                    elif isinstance(value, datetime):
                        row[field_name] = value.isoformat()
                    else:
                        row[field_name] = value
                rows.append(row)
            elif isinstance(entity, dict):
                rows.append(entity)
        return rows

    async def _reconcile(self, module: str, context: MultiOrgContext):
        """Run reconciliation checks for the module."""
        checks_config = MODULE_RECON_CHECKS.get(module, [])
        checks = []

        for check_cfg in checks_config:
            if check_cfg["type"] == "row_count":
                src_count = await self.reconciliation_port.get_source_row_count(
                    check_cfg["source_table"], context
                )
                tgt_count = await self.reconciliation_port.get_target_row_count(
                    self.bronze_dataset, check_cfg["target_table"]
                )
                checks.append(self.reconciliation_service.build_row_count_check(
                    f"Oracle {check_cfg['source_table']}",
                    f"BigQuery {self.bronze_dataset}.{check_cfg['target_table']}",
                    src_count, tgt_count,
                ))
            elif check_cfg["type"] == "aggregate":
                src_total = await self.reconciliation_port.get_source_aggregate(
                    check_cfg["source_table"], check_cfg["source_col"], context
                )
                tgt_total = await self.reconciliation_port.get_target_aggregate(
                    self.bronze_dataset, check_cfg["target_table"], check_cfg["target_col"]
                )
                checks.append(self.reconciliation_service.build_aggregate_balance_check(
                    f"Oracle {check_cfg['source_table']}.{check_cfg['source_col']}",
                    f"BigQuery {check_cfg['target_table']}.{check_cfg['target_col']}",
                    src_total, tgt_total,
                ))

        period = Period(period_name="current", period_year=2026, period_num=1)
        return self.reconciliation_service.reconcile(module, period, context, checks)

    def _build_result(self, module, period, context, success, rows_extracted=0,
                      rows_loaded=0, errors=None, steps=None, start_time=0):
        return MigrationResult(
            module=module, period=period, context=context, success=success,
            rows_extracted=rows_extracted, rows_loaded=rows_loaded,
            errors=errors or [], steps_completed=steps or [],
            duration_seconds=round(time.time() - start_time, 2),
        )
