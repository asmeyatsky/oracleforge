import logging
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from domain.ports.ai_ports import AIOrchestrationPort
from domain.ports.oracle_ports import OracleSourcePort
from domain.ports.gcp_ports import GCPTargetPort
from domain.ports.orchestration_ports import (
    AgentRole,
    AgentTask,
    AgentResult,
    OrchestrationPlan,
    OrchestrationResult,
)

logger = logging.getLogger(__name__)


# --- Pydantic schemas for structured AI outputs ---


class CustomizationFinding(BaseModel):
    """A single undocumented customization found by the Scout."""
    table_name: str
    customization_type: str  # "custom_column", "custom_index", "non_standard_trigger", etc.
    details: str
    risk_level: str  # "low", "medium", "high"


class ScoutReport(BaseModel):
    """Structured output from the Scout agent."""
    schema_name: str
    total_tables_scanned: int
    customizations: List[CustomizationFinding]
    summary: str


class MappingProposal(BaseModel):
    """A single table mapping proposed by the Architect."""
    source_table: str
    target_dataset: str  # BigQuery dataset
    target_table: str  # BigQuery table name
    transformation_notes: str
    materialization: str  # "table", "view", "incremental"
    partition_column: Optional[str] = None
    cluster_columns: List[str] = []


class ArchitectBlueprint(BaseModel):
    """Structured output from the Architect agent."""
    schema_name: str
    mappings: List[MappingProposal]
    estimated_complexity: str  # "low", "medium", "high"
    recommendations: List[str]


class ValidationCheck(BaseModel):
    """A single validation check performed by the Validator."""
    source_table: str
    check_type: str  # "schema_compatibility", "data_sample", "type_mapping"
    passed: bool
    details: str


class ValidatorReport(BaseModel):
    """Structured output from the Validator agent."""
    total_checks: int
    passed_checks: int
    failed_checks: int
    checks: List[ValidationCheck]
    ready_for_migration: bool


class CatalogEntry(BaseModel):
    """A single Dataplex catalog entry created by the Documenter."""
    asset_name: str
    asset_type: str
    description: str
    lineage_source: str
    tags: List[str]


class DocumenterReport(BaseModel):
    """Structured output from the Documenter agent."""
    entries_created: int
    catalog_entries: List[CatalogEntry]
    summary: str


# --- Individual Agent Implementations ---


class ScoutAgent:
    """Agent A: Interrogates Oracle for undocumented customizations.

    Scans the Oracle schema for non-standard columns, custom indexes,
    undocumented triggers, and other customizations that could complicate migration.
    """

    def __init__(self, oracle_port: OracleSourcePort, ai_port: AIOrchestrationPort):
        self.oracle_port = oracle_port
        self.ai_port = ai_port

    async def execute(self, task: AgentTask) -> AgentResult:
        start = time.time()
        logger.info(f"Scout Agent starting task: {task.task_id}")

        try:
            schema_name = task.input_data.get("schema_name", "APPS")
            tables = task.input_data.get("tables", [])

            # Fetch schema metadata from Oracle
            metadata = await self.oracle_port.get_schema_metadata()

            # Query for non-standard objects
            custom_objects = await self.oracle_port.execute_query(
                "SELECT object_name, object_type FROM all_objects "
                "WHERE owner = :schema AND object_type IN "
                "('TRIGGER', 'INDEX', 'SEQUENCE', 'SYNONYM') "
                "AND object_name NOT LIKE 'SYS_%'",
                {"schema": schema_name},
            )

            # Use AI to analyze findings
            prompt = (
                f"Analyze these Oracle schema objects for customizations that "
                f"could impact migration to BigQuery. Schema: {schema_name}, "
                f"Tables: {tables}, Custom objects found: {custom_objects}, "
                f"Metadata: {metadata}"
            )
            report = await self.ai_port.generate_structured_insight(prompt, ScoutReport)

            return AgentResult(
                task_id=task.task_id,
                role=AgentRole.SCOUT,
                status="success",
                output_data=report.model_dump(),
                findings=[c.details for c in report.customizations],
                duration_seconds=time.time() - start,
            )
        except Exception as e:
            logger.error(f"Scout Agent failed: {e}")
            return AgentResult(
                task_id=task.task_id,
                role=AgentRole.SCOUT,
                status="failed",
                errors=[str(e)],
                duration_seconds=time.time() - start,
            )


class ArchitectAgent:
    """Agent B: Proposes canonical mapping to BigQuery.

    Takes Scout findings and creates a mapping blueprint from Oracle tables
    to BigQuery datasets/tables with transformation specifications.
    """

    def __init__(self, ai_port: AIOrchestrationPort):
        self.ai_port = ai_port

    async def execute(self, task: AgentTask) -> AgentResult:
        start = time.time()
        logger.info(f"Architect Agent starting task: {task.task_id}")

        try:
            scout_output = task.input_data.get("scout_output", {})
            tables = task.input_data.get("tables", [])
            schema_name = task.input_data.get("schema_name", "APPS")

            prompt = (
                f"Design a BigQuery target schema for migrating Oracle schema '{schema_name}'. "
                f"Tables to migrate: {tables}. "
                f"Scout findings (customizations): {scout_output}. "
                f"Follow medallion architecture (bronze/silver/gold). "
                f"Recommend partitioning and clustering strategies."
            )
            blueprint = await self.ai_port.generate_structured_insight(prompt, ArchitectBlueprint)

            return AgentResult(
                task_id=task.task_id,
                role=AgentRole.ARCHITECT,
                status="success",
                output_data=blueprint.model_dump(),
                findings=blueprint.recommendations,
                duration_seconds=time.time() - start,
            )
        except Exception as e:
            logger.error(f"Architect Agent failed: {e}")
            return AgentResult(
                task_id=task.task_id,
                role=AgentRole.ARCHITECT,
                status="failed",
                errors=[str(e)],
                duration_seconds=time.time() - start,
            )


class ValidatorAgent:
    """Agent C: Tests the mapping with sample data.

    Validates that the proposed BigQuery schema is compatible with the Oracle
    source data by running sample queries and type compatibility checks.
    """

    def __init__(self, oracle_port: OracleSourcePort, gcp_port: GCPTargetPort, ai_port: AIOrchestrationPort):
        self.oracle_port = oracle_port
        self.gcp_port = gcp_port
        self.ai_port = ai_port

    async def execute(self, task: AgentTask) -> AgentResult:
        start = time.time()
        logger.info(f"Validator Agent starting task: {task.task_id}")

        try:
            architect_output = task.input_data.get("architect_output", {})
            tables = task.input_data.get("tables", [])

            # Sample data from Oracle for validation
            sample_results = []
            for table in tables[:5]:  # Limit to first 5 tables
                sample = await self.oracle_port.execute_query(
                    f"SELECT * FROM {table} WHERE ROWNUM <= 10"
                )
                sample_results.append({"table": table, "sample_rows": len(sample)})

            prompt = (
                f"Validate this BigQuery migration mapping against sample Oracle data. "
                f"Architect blueprint: {architect_output}. "
                f"Sample data results: {sample_results}. "
                f"Check for type compatibility, NULL handling, and data truncation risks."
            )
            report = await self.ai_port.generate_structured_insight(prompt, ValidatorReport)

            return AgentResult(
                task_id=task.task_id,
                role=AgentRole.VALIDATOR,
                status="success" if report.ready_for_migration else "partial",
                output_data=report.model_dump(),
                findings=[c.details for c in report.checks if not c.passed],
                duration_seconds=time.time() - start,
            )
        except Exception as e:
            logger.error(f"Validator Agent failed: {e}")
            return AgentResult(
                task_id=task.task_id,
                role=AgentRole.VALIDATOR,
                status="failed",
                errors=[str(e)],
                duration_seconds=time.time() - start,
            )


class DocumenterAgent:
    """Agent D: Updates the Dataplex metadata catalog automatically.

    Creates Dataplex catalog entries, documents lineage from Oracle to BigQuery,
    and tags assets with module/compliance metadata.
    """

    def __init__(self, gcp_port: GCPTargetPort, ai_port: AIOrchestrationPort):
        self.gcp_port = gcp_port
        self.ai_port = ai_port

    async def execute(self, task: AgentTask) -> AgentResult:
        start = time.time()
        logger.info(f"Documenter Agent starting task: {task.task_id}")

        try:
            architect_output = task.input_data.get("architect_output", {})
            validator_output = task.input_data.get("validator_output", {})
            schema_name = task.input_data.get("schema_name", "APPS")

            prompt = (
                f"Generate Dataplex catalog entries for the Oracle-to-BigQuery migration. "
                f"Source schema: {schema_name}. "
                f"Architecture blueprint: {architect_output}. "
                f"Validation results: {validator_output}. "
                f"Include lineage documentation and compliance tags."
            )
            report = await self.ai_port.generate_structured_insight(prompt, DocumenterReport)

            # Store catalog metadata in BigQuery for Dataplex integration
            if report.catalog_entries:
                catalog_data = [entry.model_dump() for entry in report.catalog_entries]
                await self.gcp_port.load_to_bigquery(
                    "dataplex_metadata", "catalog_entries", catalog_data
                )

            return AgentResult(
                task_id=task.task_id,
                role=AgentRole.DOCUMENTER,
                status="success",
                output_data=report.model_dump(),
                findings=[report.summary],
                duration_seconds=time.time() - start,
            )
        except Exception as e:
            logger.error(f"Documenter Agent failed: {e}")
            return AgentResult(
                task_id=task.task_id,
                role=AgentRole.DOCUMENTER,
                status="failed",
                errors=[str(e)],
                duration_seconds=time.time() - start,
            )


# --- Orchestrator ---


class MultiAgentOrchestrator:
    """Orchestrates the Scout -> Architect -> Validator -> Documenter pipeline.

    Creates a plan with dependent tasks and executes agents in sequence,
    passing outputs from earlier agents as inputs to later ones.
    """

    def __init__(
        self,
        oracle_port: OracleSourcePort,
        gcp_port: GCPTargetPort,
        ai_port: AIOrchestrationPort,
    ):
        self.scout = ScoutAgent(oracle_port, ai_port)
        self.architect = ArchitectAgent(ai_port)
        self.validator = ValidatorAgent(oracle_port, gcp_port, ai_port)
        self.documenter = DocumenterAgent(gcp_port, ai_port)

    def create_plan(self, plan_id: str, schema_name: str, tables: List[str]) -> OrchestrationPlan:
        """Create a sequential orchestration plan."""
        tasks = [
            AgentTask(
                task_id=f"{plan_id}_scout",
                role=AgentRole.SCOUT,
                description=f"Scan {schema_name} for undocumented customizations",
                input_data={"schema_name": schema_name, "tables": tables},
            ),
            AgentTask(
                task_id=f"{plan_id}_architect",
                role=AgentRole.ARCHITECT,
                description=f"Design BigQuery target schema for {schema_name}",
                input_data={"schema_name": schema_name, "tables": tables},
                depends_on=[f"{plan_id}_scout"],
            ),
            AgentTask(
                task_id=f"{plan_id}_validator",
                role=AgentRole.VALIDATOR,
                description=f"Validate mapping with sample data from {schema_name}",
                input_data={"tables": tables},
                depends_on=[f"{plan_id}_architect"],
            ),
            AgentTask(
                task_id=f"{plan_id}_documenter",
                role=AgentRole.DOCUMENTER,
                description=f"Update Dataplex catalog for {schema_name} migration",
                input_data={"schema_name": schema_name},
                depends_on=[f"{plan_id}_validator"],
            ),
        ]
        return OrchestrationPlan(plan_id=plan_id, schema_name=schema_name, tasks=tasks)

    async def execute_plan(self, plan: OrchestrationPlan) -> OrchestrationResult:
        """Execute the orchestration plan in dependency order."""
        logger.info(f"Executing orchestration plan: {plan.plan_id} ({plan.task_count} tasks)")
        results: List[AgentResult] = []
        results_by_task: Dict[str, AgentResult] = {}

        for task in plan.tasks:
            # Inject outputs from dependencies into input_data
            enriched_input = dict(task.input_data)
            for dep_id in task.depends_on:
                dep_result = results_by_task.get(dep_id)
                if dep_result:
                    dep_role = dep_result.role.value
                    enriched_input[f"{dep_role}_output"] = dep_result.output_data

            enriched_task = AgentTask(
                task_id=task.task_id,
                role=task.role,
                description=task.description,
                input_data=enriched_input,
                depends_on=task.depends_on,
            )

            # Route to correct agent
            agent_map = {
                AgentRole.SCOUT: self.scout,
                AgentRole.ARCHITECT: self.architect,
                AgentRole.VALIDATOR: self.validator,
                AgentRole.DOCUMENTER: self.documenter,
            }
            agent = agent_map[task.role]
            result = await agent.execute(enriched_task)
            results.append(result)
            results_by_task[task.task_id] = result

            # Stop if a critical agent fails
            if result.status == "failed" and task.role in (AgentRole.SCOUT, AgentRole.ARCHITECT):
                logger.error(f"Critical agent {task.role.value} failed. Stopping pipeline.")
                break

        return OrchestrationResult(plan_id=plan.plan_id, results=results)
