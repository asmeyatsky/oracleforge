"""Tests for the MigrationPipelineUseCase using mock adapters."""

import pytest
from decimal import Decimal
from domain.value_objects.common import Period, MultiOrgContext
from application.use_cases.migration_pipeline import MigrationPipelineUseCase, MigrationResult


# We import mock adapters to wire the pipeline without real Oracle/GCP
from infrastructure.adapters.mock_oracle_adapter import MockOracleAdapter
from infrastructure.adapters.mock_gcp_adapter import MockGCPAdapter
from infrastructure.adapters.mock_reconciliation_adapter import MockReconciliationAdapter
from infrastructure.adapters.logging_event_bus import LoggingEventBus


@pytest.fixture
def pipeline():
    return MigrationPipelineUseCase(
        oracle_port=MockOracleAdapter(),
        gcp_port=MockGCPAdapter(),
        reconciliation_port=MockReconciliationAdapter(),
        event_bus=LoggingEventBus(),
        bronze_dataset="bronze",
    )


@pytest.fixture
def period():
    return Period(period_name="Jan-26", period_year=2026, period_num=1)


@pytest.fixture
def context():
    return MultiOrgContext(org_id=101, set_of_books_id=1, ledger_id=2001)


@pytest.mark.asyncio
async def test_gl_migration_pipeline(pipeline, period, context):
    result = await pipeline.execute("GL", period, context)
    assert isinstance(result, MigrationResult)
    assert result.module == "GL"
    assert result.success is True
    assert result.rows_extracted > 0
    assert result.rows_loaded > 0
    assert result.reconciliation_passed is True
    assert result.certificate_id is not None
    assert result.certificate_status == "CERTIFIED"
    assert "extract" in result.steps_completed
    assert "load_bronze" in result.steps_completed
    assert "reconcile" in result.steps_completed
    assert "certify" in result.steps_completed


@pytest.mark.asyncio
async def test_ap_migration_pipeline(pipeline, period, context):
    result = await pipeline.execute("AP", period, context)
    assert result.success is True
    assert result.module == "AP"
    assert result.rows_extracted > 0
    assert result.certificate_status == "CERTIFIED"


@pytest.mark.asyncio
async def test_hcm_migration_pipeline(pipeline, period, context):
    result = await pipeline.execute("HCM", period, context)
    assert result.success is True
    assert result.module == "HCM"
    assert result.rows_extracted > 0


@pytest.mark.asyncio
async def test_dry_run_skips_loading(period, context):
    gcp = MockGCPAdapter()
    pipeline = MigrationPipelineUseCase(
        oracle_port=MockOracleAdapter(),
        gcp_port=gcp,
        reconciliation_port=MockReconciliationAdapter(),
        event_bus=LoggingEventBus(),
    )
    result = await pipeline.execute("GL", period, context, dry_run=True)
    assert result.success is True
    assert "load_bronze (dry_run)" in result.steps_completed
    # MockGCPAdapter should not have received any data
    assert len(gcp.loaded_data) == 0


@pytest.mark.asyncio
async def test_events_published(period, context):
    event_bus = LoggingEventBus()
    pipeline = MigrationPipelineUseCase(
        oracle_port=MockOracleAdapter(),
        gcp_port=MockGCPAdapter(),
        reconciliation_port=MockReconciliationAdapter(),
        event_bus=event_bus,
    )
    await pipeline.execute("GL", period, context)

    event_types = [type(e).__name__ for e in event_bus.published_events]
    assert "MigrationStartedEvent" in event_types
    assert "ExtractionCompleteEvent" in event_types
    assert "LoadCompleteEvent" in event_types
    assert "ReconciliationCompleteEvent" in event_types
    assert "MigrationCompleteEvent" in event_types


@pytest.mark.asyncio
async def test_reconciliation_mismatch_fails(period, context):
    pipeline = MigrationPipelineUseCase(
        oracle_port=MockOracleAdapter(),
        gcp_port=MockGCPAdapter(),
        reconciliation_port=MockReconciliationAdapter(simulate_mismatch=True),
        event_bus=LoggingEventBus(),
    )
    result = await pipeline.execute("GL", period, context)
    # With mismatch, reconciliation should fail
    assert result.reconciliation_passed is False
    assert result.certificate_status == "FAILED"


@pytest.mark.asyncio
async def test_pipeline_result_has_duration(pipeline, period, context):
    result = await pipeline.execute("GL", period, context)
    assert result.duration_seconds >= 0


@pytest.mark.asyncio
async def test_case_insensitive_module(pipeline, period, context):
    result = await pipeline.execute("gl", period, context)
    assert result.module == "GL"
    assert result.success is True
