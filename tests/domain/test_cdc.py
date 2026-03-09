"""Pure domain tests for CDC entities and orchestration service.

No infrastructure imports — only domain layer code is exercised here.
"""

import pytest
from datetime import datetime, timezone

from domain.entities.cdc import CDCStreamConfig, CDCStreamStatus, CDCEvent
from domain.services.cdc_service import (
    CDCOrchestrationService,
    MODULE_CDC_TABLES,
    VALID_REPLICATION_MODES,
)


@pytest.fixture
def service():
    return CDCOrchestrationService()


# ── build_stream_config ──────────────────────────────────────────────────


def test_build_stream_config_gl(service):
    config = service.build_stream_config("GL", "APPS", "bronze_gl", "my-project")
    assert config.stream_name == "cdc-gl-apps"
    assert config.source_schema == "APPS"
    assert config.target_dataset == "bronze_gl"
    assert config.target_project == "my-project"
    assert config.source_tables == MODULE_CDC_TABLES["GL"]
    assert config.replication_mode == "continuous"
    assert config.backfill is True


def test_build_stream_config_ap(service):
    config = service.build_stream_config("AP", "APPS", "bronze_ap", "proj-1")
    assert config.stream_name == "cdc-ap-apps"
    assert config.source_tables == MODULE_CDC_TABLES["AP"]
    assert len(config.source_tables) == 6


def test_build_stream_config_hcm(service):
    config = service.build_stream_config("HCM", "HR", "bronze_hcm", "proj-2")
    assert config.stream_name == "cdc-hcm-hr"
    assert config.source_tables == MODULE_CDC_TABLES["HCM"]
    assert len(config.source_tables) == 4


def test_build_stream_config_case_insensitive(service):
    config = service.build_stream_config("gl", "APPS", "ds", "proj")
    assert config.source_tables == MODULE_CDC_TABLES["GL"]


def test_build_stream_config_unknown_module(service):
    with pytest.raises(ValueError, match="Unknown module"):
        service.build_stream_config("UNKNOWN", "APPS", "ds", "proj")


# ── validate_stream_config ───────────────────────────────────────────────


def test_validate_valid_config(service):
    config = service.build_stream_config("GL", "APPS", "bronze", "proj")
    errors = service.validate_stream_config(config)
    assert errors == []


def test_validate_missing_stream_name(service):
    config = CDCStreamConfig(
        stream_name="",
        source_schema="APPS",
        source_tables=["T1"],
        target_dataset="ds",
        target_project="proj",
    )
    errors = service.validate_stream_config(config)
    assert any("stream_name" in e for e in errors)


def test_validate_missing_source_schema(service):
    config = CDCStreamConfig(
        stream_name="s1",
        source_schema="",
        source_tables=["T1"],
        target_dataset="ds",
        target_project="proj",
    )
    errors = service.validate_stream_config(config)
    assert any("source_schema" in e for e in errors)


def test_validate_empty_tables(service):
    config = CDCStreamConfig(
        stream_name="s1",
        source_schema="APPS",
        source_tables=[],
        target_dataset="ds",
        target_project="proj",
    )
    errors = service.validate_stream_config(config)
    assert any("source_tables" in e for e in errors)


def test_validate_missing_target_dataset(service):
    config = CDCStreamConfig(
        stream_name="s1",
        source_schema="APPS",
        source_tables=["T1"],
        target_dataset="",
        target_project="proj",
    )
    errors = service.validate_stream_config(config)
    assert any("target_dataset" in e for e in errors)


def test_validate_missing_target_project(service):
    config = CDCStreamConfig(
        stream_name="s1",
        source_schema="APPS",
        source_tables=["T1"],
        target_dataset="ds",
        target_project="   ",
    )
    errors = service.validate_stream_config(config)
    assert any("target_project" in e for e in errors)


def test_validate_invalid_replication_mode(service):
    config = CDCStreamConfig(
        stream_name="s1",
        source_schema="APPS",
        source_tables=["T1"],
        target_dataset="ds",
        target_project="proj",
        replication_mode="realtime",
    )
    errors = service.validate_stream_config(config)
    assert any("replication_mode" in e for e in errors)


def test_validate_multiple_errors(service):
    config = CDCStreamConfig(
        stream_name="",
        source_schema="",
        source_tables=[],
        target_dataset="",
        target_project="",
        replication_mode="bad",
    )
    errors = service.validate_stream_config(config)
    assert len(errors) == 6


# ── is_stream_healthy ────────────────────────────────────────────────────


def test_is_stream_healthy_running_with_synced_tables(service):
    status = CDCStreamStatus(
        stream_name="s1",
        status="RUNNING",
        tables_synced=3,
        total_tables=5,
    )
    assert service.is_stream_healthy(status) is True


def test_is_stream_healthy_false_when_paused(service):
    status = CDCStreamStatus(stream_name="s1", status="PAUSED", tables_synced=3, total_tables=5)
    assert service.is_stream_healthy(status) is False


def test_is_stream_healthy_false_when_errors(service):
    status = CDCStreamStatus(
        stream_name="s1",
        status="RUNNING",
        tables_synced=3,
        total_tables=5,
        errors=["connection timeout"],
    )
    assert service.is_stream_healthy(status) is False


def test_is_stream_healthy_false_when_no_tables_synced(service):
    status = CDCStreamStatus(stream_name="s1", status="RUNNING", tables_synced=0, total_tables=5)
    assert service.is_stream_healthy(status) is False


# ── calculate_sync_progress ──────────────────────────────────────────────


def test_calculate_sync_progress_partial(service):
    status = CDCStreamStatus(stream_name="s1", status="RUNNING", tables_synced=3, total_tables=6)
    assert service.calculate_sync_progress(status) == pytest.approx(0.5)


def test_calculate_sync_progress_complete(service):
    status = CDCStreamStatus(stream_name="s1", status="RUNNING", tables_synced=5, total_tables=5)
    assert service.calculate_sync_progress(status) == pytest.approx(1.0)


def test_calculate_sync_progress_zero_tables(service):
    status = CDCStreamStatus(stream_name="s1", status="NOT_STARTED", tables_synced=0, total_tables=0)
    assert service.calculate_sync_progress(status) == 0.0


def test_calculate_sync_progress_capped_at_one(service):
    status = CDCStreamStatus(stream_name="s1", status="RUNNING", tables_synced=10, total_tables=5)
    assert service.calculate_sync_progress(status) == 1.0


# ── Entity construction ──────────────────────────────────────────────────


def test_cdc_event_defaults():
    event = CDCEvent(stream_name="s1", table_name="T1", operation="INSERT")
    assert event.row_count == 1
    assert event.timestamp.tzinfo is not None


def test_cdc_stream_config_frozen():
    config = CDCStreamConfig(
        stream_name="s1",
        source_schema="APPS",
        source_tables=["T1"],
        target_dataset="ds",
        target_project="proj",
    )
    with pytest.raises(AttributeError):
        config.stream_name = "changed"


def test_cdc_stream_status_frozen():
    status = CDCStreamStatus(stream_name="s1", status="RUNNING")
    with pytest.raises(AttributeError):
        status.status = "PAUSED"
