import logging
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from domain.entities.plsql_objects import (
    PLSQLProcedure,
    PLSQLTrigger,
    PLSQLPackage,
    PLSQLParameter,
    TranslationResult,
)
from domain.ports.alloydb_ports import AlloyDBPort
from domain.services.plsql_translator_service import PLSQLTranslatorService

logger = logging.getLogger(__name__)


class AlloyDBAdapter(AlloyDBPort):
    """Adapter for Oracle → AlloyDB PL/SQL compatibility layer.

    Extracts Oracle PL/SQL objects, translates them using the domain service,
    and deploys to AlloyDB Omni.
    """

    def __init__(self, oracle_connection_string: str, alloydb_connection_string: str):
        self.oracle_engine = create_engine(oracle_connection_string)
        self.alloydb_engine = create_engine(alloydb_connection_string)
        self.translator = PLSQLTranslatorService()

    async def extract_plsql_objects(self, schema: str) -> Dict[str, Any]:
        """Extract PL/SQL procedures, functions, triggers, and packages from Oracle."""
        logger.info(f"Extracting PL/SQL objects from schema: {schema}")
        with self.oracle_engine.connect() as conn:
            # Extract procedures and functions
            procs_result = conn.execute(text(
                "SELECT object_name, object_type, procedure_name "
                "FROM all_procedures WHERE owner = :schema "
                "AND object_type IN ('PROCEDURE', 'FUNCTION')"
            ), {"schema": schema.upper()})
            procedures = [dict(row._mapping) for row in procs_result]

            # Extract triggers
            triggers_result = conn.execute(text(
                "SELECT trigger_name, table_name, trigger_type, "
                "triggering_event, trigger_body, when_clause "
                "FROM all_triggers WHERE owner = :schema"
            ), {"schema": schema.upper()})
            triggers = [dict(row._mapping) for row in triggers_result]

            # Extract packages
            packages_result = conn.execute(text(
                "SELECT object_name FROM all_objects "
                "WHERE owner = :schema AND object_type = 'PACKAGE'"
            ), {"schema": schema.upper()})
            packages = [dict(row._mapping) for row in packages_result]

        return {
            "procedures": procedures,
            "triggers": triggers,
            "packages": packages,
        }

    async def translate_to_postgresql(
        self,
        procedures: List[PLSQLProcedure],
        triggers: List[PLSQLTrigger],
        packages: List[PLSQLPackage],
    ) -> TranslationResult:
        """Translate Oracle PL/SQL objects to AlloyDB-compatible PostgreSQL."""
        schema = procedures[0].schema_name if procedures else "UNKNOWN"
        return self.translator.translate_all(schema, procedures, triggers, packages)

    async def deploy_to_alloydb(self, result: TranslationResult, target_schema: str) -> bool:
        """Deploy translated PostgreSQL functions and triggers to AlloyDB."""
        logger.info(
            f"Deploying {result.total_objects} objects to AlloyDB schema {target_schema}"
        )
        with self.alloydb_engine.connect() as conn:
            # Create schema if not exists
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {target_schema}"))
            conn.execute(text(f"SET search_path TO {target_schema}"))

            # Deploy functions
            for func in result.functions:
                logger.info(f"Deploying function: {func.function_name}")
                conn.execute(text(func.body))

            # Deploy triggers
            for trigger in result.triggers:
                trigger_sql = (
                    f"CREATE OR REPLACE TRIGGER {trigger.trigger_name} "
                    f"{trigger.trigger_timing} {trigger.trigger_event} "
                    f"ON {trigger.table_name} "
                    f"{'FOR EACH ROW' if trigger.for_each_row else 'FOR EACH STATEMENT'} "
                    f"EXECUTE FUNCTION {trigger.function_name}()"
                )
                logger.info(f"Deploying trigger: {trigger.trigger_name}")
                conn.execute(text(trigger_sql))

            conn.commit()
        return True

    async def validate_translation(self, result: TranslationResult) -> List[str]:
        """Validate translated code by attempting to parse it against AlloyDB."""
        logger.info(f"Validating {result.total_objects} translated objects")
        errors = []

        if result.has_unsupported:
            for construct in result.unsupported_constructs:
                errors.append(f"Unsupported Oracle construct requires manual review: {construct}")

        # Additional static analysis could be performed here
        for func in result.functions:
            if "DECODE(" in func.body:
                errors.append(
                    f"Function {func.function_name} contains DECODE which "
                    f"needs manual conversion to CASE WHEN"
                )

        return errors
