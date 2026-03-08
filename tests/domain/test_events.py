"""Tests for domain events — pure entity tests, no mocks."""

import pytest
from datetime import datetime, timezone
from domain.events.migration_events import (
    MigrationEvent,
    MigrationStartedEvent,
    ExtractionCompleteEvent,
    TransformationCompleteEvent,
    ComplianceCheckEvent,
    LoadCompleteEvent,
    ReconciliationCompleteEvent,
    MigrationCompleteEvent,
)


def test_migration_started_event():
    event = MigrationStartedEvent(
        event_id="run-001", module="GL", period_name="Jan-26",
        org_id=101, tables=["GL_JE_HEADERS", "GL_JE_LINES"], dry_run=False,
    )
    assert event.module == "GL"
    assert event.org_id == 101
    assert len(event.tables) == 2
    assert event.dry_run is False
    assert event.timestamp.tzinfo == timezone.utc


def test_extraction_complete_event():
    event = ExtractionCompleteEvent(
        event_id="run-001", module="AP", period_name="Jan-26",
        org_id=101, rows_extracted=5000,
        tables_extracted=["AP_INVOICES_ALL", "AP_INVOICE_LINES_ALL"],
        duration_seconds=12.5,
    )
    assert event.rows_extracted == 5000
    assert len(event.tables_extracted) == 2
    assert event.duration_seconds == 12.5


def test_load_complete_event():
    event = LoadCompleteEvent(
        event_id="run-001", module="GL", period_name="Jan-26",
        org_id=101, layer="bronze", dataset="bronze_gl",
        rows_loaded=15000, duration_seconds=8.3,
    )
    assert event.layer == "bronze"
    assert event.rows_loaded == 15000


def test_reconciliation_complete_event():
    event = ReconciliationCompleteEvent(
        event_id="run-001", module="GL", period_name="Jan-26",
        org_id=101, passed=True, total_checks=5,
        passed_checks=5, failed_checks=0,
        certificate_id="CERT-GL-2026-01",
    )
    assert event.passed is True
    assert event.total_checks == 5
    assert event.certificate_id == "CERT-GL-2026-01"


def test_migration_complete_event():
    event = MigrationCompleteEvent(
        event_id="run-001", module="GL", period_name="Jan-26",
        org_id=101, success=True, total_rows=25000,
        total_duration_seconds=45.2, certificate_id="CERT-GL-2026-01",
    )
    assert event.success is True
    assert event.total_rows == 25000
    assert event.errors == []


def test_migration_complete_event_with_errors():
    event = MigrationCompleteEvent(
        event_id="run-002", module="AP", period_name="Feb-26",
        org_id=102, success=False, errors=["Load failed", "Timeout"],
    )
    assert event.success is False
    assert len(event.errors) == 2


def test_compliance_check_event():
    event = ComplianceCheckEvent(
        event_id="run-001", module="HCM", period_name="Jan-26",
        org_id=101, standard="PDPL", passed=True,
        pii_columns_found=["email_address", "national_identifier"],
    )
    assert event.standard == "PDPL"
    assert event.passed is True
    assert len(event.pii_columns_found) == 2


def test_transformation_complete_event():
    event = TransformationCompleteEvent(
        event_id="run-001", module="GL", period_name="Jan-26",
        org_id=101, entities_resolved=500, duration_seconds=3.1,
    )
    assert event.entities_resolved == 500


def test_event_immutability():
    event = MigrationStartedEvent(
        event_id="run-001", module="GL", period_name="Jan-26", org_id=101,
    )
    with pytest.raises(AttributeError):
        event.module = "AP"
