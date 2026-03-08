class OracleForgeError(Exception):
    """Base exception for all OracleForge errors."""
    pass

class DomainError(OracleForgeError):
    """Base exception for business rule violations."""
    pass

class InfrastructureError(OracleForgeError):
    """Base exception for adapter/external service failures."""
    pass

class OrchestrationError(OracleForgeError):
    """Base exception for workflow execution failures."""
    pass
