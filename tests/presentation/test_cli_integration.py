"""Integration tests for the CLI wired to real services via mock adapters.

These tests verify that CLI commands correctly resolve services from the
DI container and produce expected results — not just hardcoded output.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from infrastructure.adapters.mock_oracle_adapter import MockOracleAdapter
from infrastructure.adapters.mock_gcp_adapter import MockGCPAdapter
from infrastructure.adapters.mock_reconciliation_adapter import MockReconciliationAdapter
from infrastructure.adapters.logging_event_bus import LoggingEventBus
from infrastructure.adapters.dbt_generator_adapter import DbtGeneratorAdapter
from domain.services.reconciliation_service import ReconciliationService
from domain.services.code_generator_service import CodeGeneratorService
from domain.services.plsql_translator_service import PLSQLTranslatorService
from application.use_cases.migration_pipeline import MigrationPipelineUseCase


runner = CliRunner()


class MockContainer:
    """Lightweight mock container for CLI testing without dependency-injector."""

    def __init__(self):
        self._oracle = MockOracleAdapter()
        self._gcp = MockGCPAdapter()
        self._recon = MockReconciliationAdapter()
        self._event_bus = LoggingEventBus()
        self._dbt = DbtGeneratorAdapter()
        self._recon_service = ReconciliationService()
        self._codegen_service = CodeGeneratorService()
        self._plsql_service = PLSQLTranslatorService()

    def oracle_adapter(self):
        return self._oracle

    def gcp_adapter(self):
        return self._gcp

    def reconciliation_adapter(self):
        return self._recon

    def reconciliation_service(self):
        return self._recon_service

    def code_generator_service(self):
        return self._codegen_service

    def plsql_translator_service(self):
        return self._plsql_service

    def dbt_generator_adapter(self):
        return self._dbt

    def migration_pipeline(self):
        return MigrationPipelineUseCase(
            oracle_port=self._oracle,
            gcp_port=self._gcp,
            reconciliation_port=self._recon,
            event_bus=self._event_bus,
            bronze_dataset="bronze",
        )

    def multi_agent_orchestrator(self):
        # Return a simple mock orchestrator for testing
        mock = MagicMock()
        from domain.ports.orchestration_ports import OrchestrationPlan, OrchestrationResult, AgentResult, AgentRole
        plan = OrchestrationPlan(plan_id="test", schema_name="APPS", tasks=[])
        mock.create_plan.return_value = plan
        result = OrchestrationResult(plan_id="test", results=[])
        mock.execute_plan = MagicMock(return_value=asyncio.coroutine(lambda: result)())
        return mock


@pytest.fixture(autouse=True)
def mock_container():
    """Patch the CLI's _get_container to use our MockContainer."""
    container = MockContainer()
    with patch("presentation.cli._get_container", return_value=container):
        # Also reset the cached container
        import presentation.cli
        presentation.cli._container = None
        yield container
        presentation.cli._container = None


def test_status_command():
    from presentation.cli import app
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "OracleForge" in result.output
    assert "Configuration" in result.output


def test_sie_classify_table_format():
    from presentation.cli import app
    result = runner.invoke(app, ["sie", "classify"])
    assert result.exit_code == 0
    assert "GL_JE_HEADERS" in result.output
    assert "AP_INVOICES_ALL" in result.output
    assert "PER_ALL_PEOPLE_F" in result.output
    assert "9 tables" in result.output


def test_sie_classify_tree_format():
    from presentation.cli import app
    result = runner.invoke(app, ["sie", "classify", "--format", "tree"])
    assert result.exit_code == 0
    assert "GL" in result.output
    assert "AP" in result.output
    assert "HCM" in result.output


def test_sie_classify_json_format():
    from presentation.cli import app
    result = runner.invoke(app, ["sie", "classify", "--format", "json"])
    assert result.exit_code == 0
    assert "GL_JE_HEADERS" in result.output


def test_sie_classify_with_pattern():
    from presentation.cli import app
    result = runner.invoke(app, ["sie", "classify", "--pattern", "GL%"])
    assert result.exit_code == 0
    assert "GL_JE_HEADERS" in result.output
    # Should not include AP or HCM tables
    assert "AP_INVOICES_ALL" not in result.output


def test_sie_flexfields():
    from presentation.cli import app
    result = runner.invoke(app, ["sie", "flexfields", "GL_CODE_COMBINATIONS"])
    assert result.exit_code == 0
    assert "Accounting Flexfield" in result.output
    assert "SEGMENT1" in result.output


def test_sie_flexfields_unknown_table():
    from presentation.cli import app
    result = runner.invoke(app, ["sie", "flexfields", "NONEXISTENT"])
    assert result.exit_code == 1


def test_migrate_run_gl():
    from presentation.cli import app
    result = runner.invoke(app, ["migrate", "run", "GL", "--period", "Jan-26"])
    assert result.exit_code == 0
    assert "COMPLETED" in result.output
    assert "CERTIFIED" in result.output
    assert "extract" in result.output


def test_migrate_run_dry_run():
    from presentation.cli import app
    result = runner.invoke(app, ["migrate", "run", "GL", "--dry-run"])
    assert result.exit_code == 0
    assert "DRY RUN" in result.output


def test_migrate_run_ap():
    from presentation.cli import app
    result = runner.invoke(app, ["migrate", "run", "AP"])
    assert result.exit_code == 0
    assert "COMPLETED" in result.output


def test_reconcile_run():
    from presentation.cli import app
    result = runner.invoke(app, ["reconcile", "run", "GL"])
    assert result.exit_code == 0
    assert "Reconciliation" in result.output
    assert "CERT-GL" in result.output


def test_codegen_dbt():
    from presentation.cli import app
    result = runner.invoke(app, ["codegen", "dbt", "GL"])
    assert result.exit_code == 0
    assert "stg_gl_je_headers" in result.output
    assert "Generated" in result.output


def test_codegen_dbt_staging_only():
    from presentation.cli import app
    result = runner.invoke(app, ["codegen", "dbt", "GL", "--layer", "staging"])
    assert result.exit_code == 0
    assert "stg_" in result.output


def test_alloydb_translate():
    from presentation.cli import app
    result = runner.invoke(app, ["alloydb", "translate", "APPS"])
    assert result.exit_code == 0
    assert "Translation" in result.output


def test_fitness_check():
    from presentation.cli import app
    result = runner.invoke(app, ["fitness", "check"])
    assert result.exit_code == 0
    assert "Rule 1" in result.output
    assert "PASS" in result.output
