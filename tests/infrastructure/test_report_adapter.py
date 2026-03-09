"""Tests for the DocxReportAdapter — certificate and migration summary reports."""

import os
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from domain.entities.reconciliation import (
    CertificateOfAccuracy,
    ReconciliationCheck,
    ReconciliationResult,
)
from domain.value_objects.common import MultiOrgContext, Period
from infrastructure.adapters.report_adapter import DocxReportAdapter
from application.use_cases.migration_pipeline import MigrationResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_checks(pass_all: bool = True):
    """Build a small list of ReconciliationCheck instances."""
    checks = [
        ReconciliationCheck(
            check_type="row_count",
            source_label="Oracle GL_JE_HEADERS",
            target_label="BigQuery bronze.gl_je_headers",
            source_value=Decimal("15000"),
            target_value=Decimal("15000"),
            tolerance=Decimal("0"),
        ),
        ReconciliationCheck(
            check_type="aggregate_balance",
            source_label="Oracle GL_JE_LINES.ACCOUNTED_DR",
            target_label="BigQuery gl_je_lines.accounted_dr",
            source_value=Decimal("5000000.00"),
            target_value=Decimal("5000000.00") if pass_all else Decimal("4800000.00"),
            tolerance=Decimal("0.01"),
        ),
    ]
    return checks


def _make_period():
    return Period(period_name="JAN-26", period_year=2026, period_num=1)


def _make_context():
    return MultiOrgContext(org_id=101, set_of_books_id=2001, ledger_id=3001)


def _make_certificate(pass_all: bool = True) -> CertificateOfAccuracy:
    period = _make_period()
    context = _make_context()
    checks = _make_checks(pass_all=pass_all)
    result = ReconciliationResult(
        module="GL",
        period=period,
        context=context,
        checks=checks,
        executed_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    return CertificateOfAccuracy(
        certificate_id="CERT-GL-2026-01-abc123",
        module="GL",
        period=period,
        context=context,
        result=result,
        issued_at=datetime(2026, 1, 15, 12, 5, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Certificate report tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_certificate_report_creates_file(tmp_path):
    """A .docx file should be created for a passing certificate."""
    adapter = DocxReportAdapter()
    cert = _make_certificate(pass_all=True)
    result_path = await adapter.generate_certificate_report(cert, str(tmp_path))

    assert os.path.isfile(result_path)
    assert result_path.endswith(".docx")


@pytest.mark.asyncio
async def test_generate_certificate_report_uses_certificate_id_as_filename(tmp_path):
    """When output_path is a directory, file name should derive from certificate_id."""
    adapter = DocxReportAdapter()
    cert = _make_certificate(pass_all=True)
    result_path = await adapter.generate_certificate_report(cert, str(tmp_path))

    assert os.path.basename(result_path) == f"{cert.certificate_id}.docx"


@pytest.mark.asyncio
async def test_generate_certificate_report_explicit_path(tmp_path):
    """When output_path is a full file path, use it as-is."""
    adapter = DocxReportAdapter()
    cert = _make_certificate(pass_all=True)
    explicit = str(tmp_path / "my_report.docx")
    result_path = await adapter.generate_certificate_report(cert, explicit)

    assert result_path == explicit
    assert os.path.isfile(result_path)


@pytest.mark.asyncio
async def test_generate_certificate_report_failed_certificate(tmp_path):
    """A failing certificate should still produce a valid .docx file."""
    adapter = DocxReportAdapter()
    cert = _make_certificate(pass_all=False)

    assert cert.status == "FAILED"

    result_path = await adapter.generate_certificate_report(cert, str(tmp_path))
    assert os.path.isfile(result_path)
    assert result_path.endswith(".docx")


@pytest.mark.asyncio
async def test_certificate_report_file_not_empty(tmp_path):
    """Generated document should have non-trivial size."""
    adapter = DocxReportAdapter()
    cert = _make_certificate(pass_all=True)
    result_path = await adapter.generate_certificate_report(cert, str(tmp_path))

    size = os.path.getsize(result_path)
    assert size > 0


# ---------------------------------------------------------------------------
# Migration summary report tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_migration_summary_creates_file(tmp_path):
    """A .docx summary should be created from multiple MigrationResult objects."""
    adapter = DocxReportAdapter()
    period = _make_period()
    context = _make_context()
    results = [
        MigrationResult(
            module="GL", period=period, context=context, success=True,
            rows_extracted=15000, rows_loaded=15000,
            reconciliation_passed=True,
            certificate_id="CERT-GL-2026-01-aaa",
            duration_seconds=42.5,
        ),
        MigrationResult(
            module="AP", period=period, context=context, success=True,
            rows_extracted=8000, rows_loaded=8000,
            reconciliation_passed=False,
            certificate_id="CERT-AP-2026-01-bbb",
            duration_seconds=31.2,
        ),
    ]

    result_path = await adapter.generate_migration_summary(results, str(tmp_path))

    assert os.path.isfile(result_path)
    assert result_path.endswith(".docx")


@pytest.mark.asyncio
async def test_migration_summary_default_filename(tmp_path):
    """When output_path is a directory, the default name should be migration_summary.docx."""
    adapter = DocxReportAdapter()
    period = _make_period()
    context = _make_context()
    results = [
        MigrationResult(
            module="HCM", period=period, context=context, success=True,
            rows_extracted=500, rows_loaded=500,
            reconciliation_passed=True,
            certificate_id="CERT-HCM-2026-01-ccc",
            duration_seconds=10.0,
        ),
    ]
    result_path = await adapter.generate_migration_summary(results, str(tmp_path))

    assert os.path.basename(result_path) == "migration_summary.docx"


@pytest.mark.asyncio
async def test_migration_summary_file_not_empty(tmp_path):
    """Generated summary document should have non-trivial size."""
    adapter = DocxReportAdapter()
    period = _make_period()
    context = _make_context()
    results = [
        MigrationResult(
            module="GL", period=period, context=context, success=True,
            rows_extracted=1000, rows_loaded=1000,
            reconciliation_passed=True,
            certificate_id="CERT-GL-2026-01-xxx",
            duration_seconds=5.0,
        ),
    ]
    result_path = await adapter.generate_migration_summary(results, str(tmp_path))

    size = os.path.getsize(result_path)
    assert size > 0
