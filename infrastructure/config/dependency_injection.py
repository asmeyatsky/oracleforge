from dependency_injector import containers, providers
from infrastructure.adapters.oracle_adapter import OracleInterrogatorAdapter
from infrastructure.adapters.mock_oracle_adapter import MockOracleAdapter
from infrastructure.adapters.gcp_adapters import GCPTargetAdapter
from infrastructure.adapters.mock_gcp_adapter import MockGCPAdapter
from infrastructure.adapters.secret_adapter import GCPSecretAdapter
from infrastructure.adapters.reconciliation_adapter import ReconciliationAdapter
from infrastructure.adapters.mock_reconciliation_adapter import MockReconciliationAdapter
from infrastructure.adapters.dbt_generator_adapter import DbtGeneratorAdapter
from infrastructure.adapters.alloydb_adapter import AlloyDBAdapter
from infrastructure.adapters.vertex_ai_adapter import VertexAIAdapter
from infrastructure.adapters.logging_event_bus import LoggingEventBus
from domain.services.org_service import MultiOrgResolver
from domain.services.reconciliation_service import ReconciliationService
from domain.services.code_generator_service import CodeGeneratorService
from domain.services.plsql_translator_service import PLSQLTranslatorService
from infrastructure.mcp_servers.sie_server import OracleForgeSIEServer
from application.use_cases.ai_workflows.multi_agent_orchestrator import MultiAgentOrchestrator
from application.use_cases.migration_pipeline import MigrationPipelineUseCase


class Container(containers.DeclarativeContainer):
    """
    Dependency Injection Container for OracleForge.

    Wiring for all domain ports and infrastructure adapters
    as per skill2026.md Rule 2 (Interface-First Development).
    """

    config = providers.Configuration()

    # Infrastructure Adapters
    # Oracle Adapter (mock/real selector)
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

    # GCP Adapter (mock/real selector)
    gcp_adapter = providers.Singleton(
        providers.Selector(
            config.use_mock_gcp,
            mock=providers.Factory(MockGCPAdapter),
            real=providers.Factory(
                GCPTargetAdapter,
                project_id=config.gcp.project_id
            )
        )
    )

    # Reconciliation Adapter (mock/real selector)
    reconciliation_adapter = providers.Singleton(
        providers.Selector(
            config.use_mock_reconciliation,
            mock=providers.Factory(MockReconciliationAdapter),
            real=providers.Factory(
                ReconciliationAdapter,
                oracle_connection_string=config.oracle.connection_string,
                gcp_project_id=config.gcp.project_id
            )
        )
    )

    # Secret Manager Adapter
    secret_adapter = providers.Singleton(
        GCPSecretAdapter,
        project_id=config.gcp.project_id
    )

    # Vertex AI Adapter
    vertex_ai_adapter = providers.Singleton(
        VertexAIAdapter,
        project_id=config.gcp.project_id,
        location=config.gcp.region
    )

    # dbt Generator Adapter
    dbt_generator_adapter = providers.Singleton(
        DbtGeneratorAdapter,
        output_base_dir=config.dbt.output_dir
    )

    # AlloyDB Adapter
    alloydb_adapter = providers.Singleton(
        AlloyDBAdapter,
        oracle_connection_string=config.oracle.connection_string,
        alloydb_connection_string=config.alloydb.connection_string
    )

    # Event Bus
    event_bus = providers.Singleton(LoggingEventBus)

    # Domain Services
    org_resolver = providers.Factory(
        MultiOrgResolver,
        oracle_port=oracle_adapter
    )

    reconciliation_service = providers.Factory(ReconciliationService)

    code_generator_service = providers.Factory(CodeGeneratorService)

    plsql_translator_service = providers.Factory(PLSQLTranslatorService)

    # Application Use Cases
    migration_pipeline = providers.Factory(
        MigrationPipelineUseCase,
        oracle_port=oracle_adapter,
        gcp_port=gcp_adapter,
        reconciliation_port=reconciliation_adapter,
        event_bus=event_bus,
        bronze_dataset=config.gcp.bronze_dataset,
    )

    multi_agent_orchestrator = providers.Factory(
        MultiAgentOrchestrator,
        oracle_port=oracle_adapter,
        gcp_port=gcp_adapter,
        ai_port=vertex_ai_adapter
    )

    # MCP Servers
    sie_server = providers.Singleton(
        OracleForgeSIEServer,
        oracle_port=oracle_adapter
    )
