import hashlib
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional
from domain.entities.reconciliation import (
    ReconciliationCheck,
    ReconciliationResult,
    CertificateOfAccuracy,
)
from domain.value_objects.common import Period, MultiOrgContext

logger = logging.getLogger(__name__)


class ReconciliationService:
    """Domain service for post-migration data reconciliation.

    Compares row counts, checksums, and aggregate balances between
    Oracle source and BigQuery target to produce a Certificate of Accuracy.
    """

    def build_row_count_check(
        self,
        source_label: str,
        target_label: str,
        source_count: int,
        target_count: int,
    ) -> ReconciliationCheck:
        """Build a row-count reconciliation check."""
        return ReconciliationCheck(
            check_type="row_count",
            source_label=source_label,
            target_label=target_label,
            source_value=Decimal(str(source_count)),
            target_value=Decimal(str(target_count)),
            tolerance=Decimal("0"),  # Row counts must match exactly
        )

    def build_checksum_check(
        self,
        source_label: str,
        target_label: str,
        source_checksum: str,
        target_checksum: str,
    ) -> ReconciliationCheck:
        """Build a checksum reconciliation check.

        Checksums are compared as equality; we encode match as 1/1 and mismatch as 0/1.
        """
        match_val = Decimal("1") if source_checksum == target_checksum else Decimal("0")
        return ReconciliationCheck(
            check_type="checksum",
            source_label=source_label,
            target_label=target_label,
            source_value=Decimal("1"),  # expected
            target_value=match_val,
            tolerance=Decimal("0"),
        )

    def build_aggregate_balance_check(
        self,
        source_label: str,
        target_label: str,
        source_total: Decimal,
        target_total: Decimal,
        tolerance: Decimal = Decimal("0.01"),
    ) -> ReconciliationCheck:
        """Build an aggregate balance reconciliation check (e.g., total credits)."""
        return ReconciliationCheck(
            check_type="aggregate_balance",
            source_label=source_label,
            target_label=target_label,
            source_value=source_total,
            target_value=target_total,
            tolerance=tolerance,
        )

    def reconcile(
        self,
        module: str,
        period: Period,
        context: MultiOrgContext,
        checks: List[ReconciliationCheck],
    ) -> ReconciliationResult:
        """Run all reconciliation checks and produce a result."""
        logger.info(
            f"Running {len(checks)} reconciliation checks for {module} "
            f"period {period.period_name}"
        )
        return ReconciliationResult(
            module=module,
            period=period,
            context=context,
            checks=checks,
        )

    def issue_certificate(
        self,
        result: ReconciliationResult,
        certificate_id: str,
    ) -> CertificateOfAccuracy:
        """Issue a Certificate of Accuracy from a reconciliation result."""
        cert = CertificateOfAccuracy(
            certificate_id=certificate_id,
            module=result.module,
            period=result.period,
            context=result.context,
            result=result,
        )
        logger.info(f"Issued certificate: {cert.summary}")
        return cert
