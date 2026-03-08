"""OracleForge exception hierarchy.

All exceptions inherit from OracleForgeError for unified error handling.
Domain errors represent business rule violations.
Infrastructure errors represent adapter/external service failures.
Orchestration errors represent workflow execution failures.
"""


class OracleForgeError(Exception):
    """Base exception for all OracleForge errors."""

    def __init__(self, message: str, details: str = "", retryable: bool = False):
        super().__init__(message)
        self.details = details
        self.retryable = retryable


class DomainError(OracleForgeError):
    """Base exception for business rule violations."""
    pass


class InfrastructureError(OracleForgeError):
    """Base exception for adapter/external service failures."""
    pass


class OrchestrationError(OracleForgeError):
    """Base exception for workflow execution failures."""
    pass


# --- Domain Errors ---


class ReconciliationError(DomainError):
    """Raised when reconciliation checks fail."""

    def __init__(self, message: str, failed_checks: int = 0, total_checks: int = 0):
        super().__init__(message, details=f"{failed_checks}/{total_checks} checks failed")
        self.failed_checks = failed_checks
        self.total_checks = total_checks


class ComplianceError(DomainError):
    """Raised when PDPL/NDMO/SAMA/GDPR compliance checks fail."""

    def __init__(self, message: str, standard: str = "", violations: list = None):
        super().__init__(message, details=f"Standard: {standard}")
        self.standard = standard
        self.violations = violations or []


class TranslationError(DomainError):
    """Raised when PL/SQL to PostgreSQL translation fails."""

    def __init__(self, message: str, source_object: str = "", unsupported: list = None):
        super().__init__(message, details=f"Object: {source_object}")
        self.source_object = source_object
        self.unsupported = unsupported or []


class EntityResolutionError(DomainError):
    """Raised when raw Oracle data cannot be mapped to a domain entity."""

    def __init__(self, message: str, entity_type: str = "", missing_fields: list = None):
        super().__init__(message, details=f"Entity: {entity_type}")
        self.entity_type = entity_type
        self.missing_fields = missing_fields or []


# --- Infrastructure Errors ---


class ConnectionError(InfrastructureError):
    """Raised when Oracle or GCP connection fails."""

    def __init__(self, message: str, target: str = ""):
        super().__init__(message, details=f"Target: {target}", retryable=True)
        self.target = target


class ExtractionError(InfrastructureError):
    """Raised when data extraction from Oracle fails."""

    def __init__(self, message: str, table: str = "", query: str = ""):
        super().__init__(message, details=f"Table: {table}", retryable=True)
        self.table = table
        self.query = query


class LoadError(InfrastructureError):
    """Raised when data loading to BigQuery fails."""

    def __init__(self, message: str, dataset: str = "", table: str = ""):
        super().__init__(message, details=f"Target: {dataset}.{table}", retryable=True)
        self.dataset = dataset
        self.table = table


class SecretAccessError(InfrastructureError):
    """Raised when Secret Manager access fails."""

    def __init__(self, message: str, secret_name: str = ""):
        super().__init__(message, details=f"Secret: {secret_name}", retryable=True)
        self.secret_name = secret_name


# --- Orchestration Errors ---


class AgentExecutionError(OrchestrationError):
    """Raised when an agent in the multi-agent pipeline fails."""

    def __init__(self, message: str, agent_role: str = "", task_id: str = ""):
        super().__init__(message, details=f"Agent: {agent_role}, Task: {task_id}")
        self.agent_role = agent_role
        self.task_id = task_id


class PipelineError(OrchestrationError):
    """Raised when the migration pipeline encounters a fatal error."""

    def __init__(self, message: str, step: str = "", module: str = ""):
        super().__init__(message, details=f"Step: {step}, Module: {module}")
        self.step = step
        self.module = module
