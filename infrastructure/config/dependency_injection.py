from dependency_injector import containers, providers
from infrastructure.adapters.oracle_adapter import OracleInterrogatorAdapter
from infrastructure.adapters.mock_oracle_adapter import MockOracleAdapter
from infrastructure.adapters.gcp_adapters import GCPTargetAdapter
from infrastructure.adapters.secret_adapter import GCPSecretAdapter
from domain.services.org_service import MultiOrgResolver
from infrastructure.mcp_servers.sie_server import OracleForgeSIEServer

class Container(containers.DeclarativeContainer):
    """
    Dependency Injection Container for OracleForge.
    
    Wiring for all domain ports and infrastructure adapters 
    as per skill2026.md Rule 2 (Interface-First Development).
    """
    
    config = providers.Configuration()
    
    # Infrastructure Adapters
    # Oracle Adapter
    oracle_adapter = providers.Singleton(
        providers.Selector(
            config.use_mock_oracle,
            mock=providers.Factory(MockOracleAdapter),
            real=providers.Factory(
                OracleInterrogatorAdapter,
                connection_string=config.oracle.connection_string
            )
        )
    )

    # GCP Adapter
    gcp_adapter = providers.Singleton(
        GCPTargetAdapter,
        project_id=config.gcp.project_id
    )

    # Secret Manager Adapter
    secret_adapter = providers.Singleton(
        GCPSecretAdapter,
        project_id=config.gcp.project_id
    )

    # Domain Services
    org_resolver = providers.Factory(
        MultiOrgResolver,
        oracle_port=oracle_adapter
    )

    # MCP Servers
    sie_server = providers.Singleton(
        OracleForgeSIEServer,
        oracle_port=oracle_adapter
    )
