import pytest
from datetime import datetime
from decimal import Decimal
from domain.entities.reconciliation import (
    ReconciliationCheck,
    ReconciliationResult,
    CertificateOfAccuracy,
)
from domain.value_objects.common import Money, MultiOrgContext, Period
from domain.services.reconciliation_service import ReconciliationService


@pytest.fixture
def sample_context():
    return MultiOrgContext(org_id=101, set_of_books_id=1)


@pytest.fixture
def sample_period():
    return Period(period_name="Jan-26", period_year=2026, period_num=1)


@pytest.fixture
def service():
    return ReconciliationService()


# --- Entity Tests ---


def test_reconciliation_check_within_tolerance():
    check = ReconciliationCheck(
        check_type="aggregate_balance",
        source_label="Oracle GL_BALANCES",
        target_label="BigQuery gold.gl_balances",
        source_value=Decimal("1000000.00"),
        target_value=Decimal("1000000.00"),
    )
    assert check.is_within_tolerance is True
    assert check.variance == Decimal("0.00")
    assert check.variance_pct == Decimal("0")


def test_reconciliation_check_outside_tolerance():
    check = ReconciliationCheck(
        check_type="aggregate_balance",
        source_label="Oracle AP_INVOICES_ALL",
        target_label="BigQuery gold.ap_invoices",
        source_value=Decimal("500000.00"),
        target_value=Decimal("499000.00"),
        tolerance=Decimal("0.01"),
    )
    assert check.is_within_tolerance is False
    assert check.variance == Decimal("1000.00")


def test_reconciliation_check_row_count_exact():
    check = ReconciliationCheck(
        check_type="row_count",
        source_label="Oracle GL_JE_HEADERS",
        target_label="BigQuery bronze.gl_je_headers",
        source_value=Decimal("15000"),
        target_value=Decimal("15000"),
        tolerance=Decimal("0"),
    )
    assert check.is_within_tolerance is True


def test_reconciliation_check_row_count_mismatch():
    check = ReconciliationCheck(
        check_type="row_count",
        source_label="Oracle GL_JE_HEADERS",
        target_label="BigQuery bronze.gl_je_headers",
        source_value=Decimal("15000"),
        target_value=Decimal("14998"),
        tolerance=Decimal("0"),
    )
    assert check.is_within_tolerance is False
    assert check.variance == Decimal("2")


def test_reconciliation_result_all_passed(sample_context, sample_period):
    checks = [
        ReconciliationCheck("row_count", "src", "tgt", Decimal("100"), Decimal("100"), Decimal("0")),
        ReconciliationCheck("aggregate_balance", "src", "tgt", Decimal("5000.00"), Decimal("5000.00")),
    ]
    result = ReconciliationResult(
        module="GL", period=sample_period, context=sample_context, checks=checks
    )
    assert result.passed is True
    assert result.total_checks == 2
    assert result.passed_checks_count == 2
    assert result.failed_checks == []


def test_reconciliation_result_partial_failure(sample_context, sample_period):
    checks = [
        ReconciliationCheck("row_count", "src", "tgt", Decimal("100"), Decimal("100"), Decimal("0")),
        ReconciliationCheck("aggregate_balance", "src", "tgt", Decimal("5000.00"), Decimal("4000.00")),
    ]
    result = ReconciliationResult(
        module="AP", period=sample_period, context=sample_context, checks=checks
    )
    assert result.passed is False
    assert result.passed_checks_count == 1
    assert len(result.failed_checks) == 1


# --- Service Tests ---


def test_service_build_row_count_check(service):
    check = service.build_row_count_check("Oracle T1", "BQ T1", 500, 500)
    assert check.check_type == "row_count"
    assert check.is_within_tolerance is True
    assert check.tolerance == Decimal("0")


def test_service_build_checksum_match(service):
    check = service.build_checksum_check("Oracle T1", "BQ T1", "abc123", "abc123")
    assert check.is_within_tolerance is True


def test_service_build_checksum_mismatch(service):
    check = service.build_checksum_check("Oracle T1", "BQ T1", "abc123", "xyz789")
    assert check.is_within_tolerance is False


def test_service_build_aggregate_balance_check(service):
    check = service.build_aggregate_balance_check(
        "Oracle Credits", "BQ Credits",
        Decimal("1234567.89"), Decimal("1234567.89"),
    )
    assert check.is_within_tolerance is True


def test_service_reconcile(service, sample_context, sample_period):
    checks = [
        service.build_row_count_check("Oracle GL", "BQ GL", 1000, 1000),
        service.build_aggregate_balance_check(
            "Oracle Total DR", "BQ Total DR",
            Decimal("999999.99"), Decimal("999999.99"),
        ),
    ]
    result = service.reconcile("GL", sample_period, sample_context, checks)
    assert result.passed is True
    assert result.module == "GL"


def test_service_issue_certificate_certified(service, sample_context, sample_period):
    checks = [
        service.build_row_count_check("src", "tgt", 100, 100),
        service.build_aggregate_balance_check("src", "tgt", Decimal("50000"), Decimal("50000")),
    ]
    result = service.reconcile("GL", sample_period, sample_context, checks)
    cert = service.issue_certificate(result, "CERT-GL-2026-01-001")
    assert cert.status == "CERTIFIED"
    assert "CERT-GL-2026-01-001" in cert.summary
    assert cert.issuer == "OracleForge Reconciliation Engine v1.0"


def test_service_issue_certificate_failed(service, sample_context, sample_period):
    checks = [
        service.build_row_count_check("src", "tgt", 100, 95),
    ]
    result = service.reconcile("AP", sample_period, sample_context, checks)
    cert = service.issue_certificate(result, "CERT-AP-2026-01-001")
    assert cert.status == "FAILED"


def test_variance_pct_calculation():
    check = ReconciliationCheck(
        check_type="aggregate_balance",
        source_label="src", target_label="tgt",
        source_value=Decimal("1000"),
        target_value=Decimal("990"),
    )
    assert check.variance_pct == Decimal("1.0")


def test_variance_pct_zero_source():
    check = ReconciliationCheck(
        check_type="aggregate_balance",
        source_label="src", target_label="tgt",
        source_value=Decimal("0"),
        target_value=Decimal("0"),
    )
    assert check.variance_pct == Decimal("0")


def test_variance_pct_zero_source_nonzero_target():
    check = ReconciliationCheck(
        check_type="aggregate_balance",
        source_label="src", target_label="tgt",
        source_value=Decimal("0"),
        target_value=Decimal("100"),
    )
    assert check.variance_pct == Decimal("100")
