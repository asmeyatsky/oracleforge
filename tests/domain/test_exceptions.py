import pytest
from domain.exceptions import (
    OracleForgeError,
    DomainError,
    InfrastructureError,
    OrchestrationError,
    ReconciliationError,
    ComplianceError,
    TranslationError,
    EntityResolutionError,
    ConnectionError,
    ExtractionError,
    LoadError,
    SecretAccessError,
    AgentExecutionError,
    PipelineError,
)


def test_base_error():
    err = OracleForgeError("something failed", details="context", retryable=True)
    assert str(err) == "something failed"
    assert err.details == "context"
    assert err.retryable is True


def test_base_error_defaults():
    err = OracleForgeError("fail")
    assert err.details == ""
    assert err.retryable is False


def test_domain_error_hierarchy():
    err = DomainError("business rule violated")
    assert isinstance(err, OracleForgeError)


def test_infrastructure_error_hierarchy():
    err = InfrastructureError("adapter failed")
    assert isinstance(err, OracleForgeError)


def test_reconciliation_error():
    err = ReconciliationError("3 checks failed", failed_checks=3, total_checks=10)
    assert isinstance(err, DomainError)
    assert err.failed_checks == 3
    assert err.total_checks == 10
    assert "3/10" in err.details


def test_compliance_error():
    err = ComplianceError("PII exposed", standard="PDPL", violations=["email column"])
    assert isinstance(err, DomainError)
    assert err.standard == "PDPL"
    assert err.violations == ["email column"]


def test_translation_error():
    err = TranslationError("cannot translate", source_object="APPS.CALC_TAX",
                           unsupported=["DBMS_SQL"])
    assert isinstance(err, DomainError)
    assert err.source_object == "APPS.CALC_TAX"
    assert err.unsupported == ["DBMS_SQL"]


def test_entity_resolution_error():
    err = EntityResolutionError("missing field", entity_type="Invoice",
                                missing_fields=["vendor_id"])
    assert isinstance(err, DomainError)
    assert err.entity_type == "Invoice"
    assert err.missing_fields == ["vendor_id"]


def test_connection_error():
    err = ConnectionError("timeout", target="Oracle EBS")
    assert isinstance(err, InfrastructureError)
    assert err.retryable is True
    assert err.target == "Oracle EBS"


def test_extraction_error():
    err = ExtractionError("query failed", table="GL_JE_HEADERS", query="SELECT *")
    assert isinstance(err, InfrastructureError)
    assert err.retryable is True
    assert err.table == "GL_JE_HEADERS"


def test_load_error():
    err = LoadError("BQ rejected", dataset="bronze", table="gl_journals")
    assert isinstance(err, InfrastructureError)
    assert err.retryable is True
    assert err.dataset == "bronze"
    assert err.table == "gl_journals"


def test_secret_access_error():
    err = SecretAccessError("permission denied", secret_name="oracle-db-prod")
    assert isinstance(err, InfrastructureError)
    assert err.secret_name == "oracle-db-prod"


def test_agent_execution_error():
    err = AgentExecutionError("AI timeout", agent_role="scout", task_id="PLAN-001_scout")
    assert isinstance(err, OrchestrationError)
    assert err.agent_role == "scout"
    assert err.task_id == "PLAN-001_scout"


def test_pipeline_error():
    err = PipelineError("extraction failed", step="extract", module="GL")
    assert isinstance(err, OrchestrationError)
    assert err.step == "extract"
    assert err.module == "GL"


def test_all_errors_are_oracleforge_errors():
    """Verify the full hierarchy is catchable with OracleForgeError."""
    errors = [
        ReconciliationError("x"),
        ComplianceError("x"),
        TranslationError("x"),
        EntityResolutionError("x"),
        ConnectionError("x"),
        ExtractionError("x"),
        LoadError("x"),
        SecretAccessError("x"),
        AgentExecutionError("x"),
        PipelineError("x"),
    ]
    for err in errors:
        assert isinstance(err, OracleForgeError)
