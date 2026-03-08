import logging
import re
from typing import List, Dict, Tuple
from domain.entities.plsql_objects import (
    PLSQLProcedure,
    PLSQLTrigger,
    PLSQLPackage,
    PLSQLParameter,
    PostgresFunction,
    PostgresTrigger,
    TranslationResult,
)

logger = logging.getLogger(__name__)

# Oracle → PostgreSQL type mapping
ORACLE_TO_PG_TYPE_MAP: Dict[str, str] = {
    "VARCHAR2": "VARCHAR",
    "NVARCHAR2": "VARCHAR",
    "NUMBER": "NUMERIC",
    "INTEGER": "INTEGER",
    "PLS_INTEGER": "INTEGER",
    "BINARY_INTEGER": "INTEGER",
    "FLOAT": "DOUBLE PRECISION",
    "BINARY_FLOAT": "REAL",
    "BINARY_DOUBLE": "DOUBLE PRECISION",
    "DATE": "TIMESTAMP",
    "TIMESTAMP": "TIMESTAMP",
    "CLOB": "TEXT",
    "NCLOB": "TEXT",
    "BLOB": "BYTEA",
    "RAW": "BYTEA",
    "BOOLEAN": "BOOLEAN",
    "CHAR": "CHAR",
    "NCHAR": "CHAR",
    "LONG": "TEXT",
    "XMLTYPE": "XML",
    "ROWID": "TEXT",
    "SYS_REFCURSOR": "REFCURSOR",
}

# PL/SQL → PL/pgSQL syntax replacements
SYNTAX_REPLACEMENTS: List[Tuple[str, str]] = [
    (r"\bNVL\(", "COALESCE("),
    (r"\bNVL2\(([^,]+),\s*([^,]+),\s*([^)]+)\)", r"CASE WHEN \1 IS NOT NULL THEN \2 ELSE \3 END"),
    (r"\bDECODE\(", "-- DECODE requires manual conversion: DECODE("),
    (r"\bSYSDATE\b", "CURRENT_TIMESTAMP"),
    (r"\bSYSTIMESTAMP\b", "CURRENT_TIMESTAMP"),
    (r"\bTO_DATE\(", "TO_TIMESTAMP("),
    (r"\bTO_CHAR\(", "TO_CHAR("),  # Compatible but may need format mask changes
    (r"\bDBMS_OUTPUT\.PUT_LINE\(", "RAISE NOTICE '%', ("),
    (r"\bRAISE_APPLICATION_ERROR\s*\(\s*-?\d+\s*,\s*", "RAISE EXCEPTION "),
    (r":NEW\.", "NEW."),
    (r":OLD\.", "OLD."),
    (r"\bIS\s+TABLE\s+OF\b", "[]"),  # PL/SQL collection → PG array (simplified)
    (r"\bVARCHAR2\b", "VARCHAR"),
    (r"\bNUMBER\b", "NUMERIC"),
    (r"\bINTEGER\b", "INTEGER"),
]

# Constructs that cannot be auto-translated
UNSUPPORTED_PATTERNS: List[Tuple[str, str]] = [
    (r"\bDBMS_SQL\b", "DBMS_SQL dynamic SQL package"),
    (r"\bUTL_FILE\b", "UTL_FILE file I/O package"),
    (r"\bDBMS_PIPE\b", "DBMS_PIPE inter-session messaging"),
    (r"\bDBMS_JOB\b", "DBMS_JOB scheduling (use pg_cron)"),
    (r"\bDBMS_LOB\b", "DBMS_LOB large object manipulation"),
    (r"\bAUTONOMOUS_TRANSACTION\b", "Autonomous transactions (use dblink)"),
    (r"\bBULK\s+COLLECT\b", "BULK COLLECT (use array aggregation)"),
    (r"\bFORALL\b", "FORALL bulk DML (use INSERT...SELECT)"),
    (r"\bPIPELINED\b", "Pipelined table functions (use RETURNS TABLE)"),
    (r"\bRESULT_CACHE\b", "Result cache (not supported in PG)"),
]


class PLSQLTranslatorService:
    """Domain service that translates Oracle PL/SQL to AlloyDB-compatible PostgreSQL.

    Handles type mapping, syntax conversion, trigger restructuring,
    and package decomposition.
    """

    def map_parameter_type(self, oracle_type: str) -> str:
        """Map an Oracle PL/SQL type to PostgreSQL equivalent."""
        base_type = oracle_type.split("(")[0].upper().strip()
        return ORACLE_TO_PG_TYPE_MAP.get(base_type, oracle_type)

    def translate_parameter_list(self, params: List[PLSQLParameter]) -> str:
        """Convert Oracle procedure parameters to PostgreSQL function parameters."""
        if not params:
            return ""
        pg_params = []
        for p in params:
            pg_type = self.map_parameter_type(p.data_type)
            direction = ""
            if p.direction == "OUT":
                direction = "OUT "
            elif p.direction == "IN OUT":
                direction = "INOUT "
            param_str = f"{direction}{p.name} {pg_type}"
            if p.default_value:
                param_str += f" DEFAULT {p.default_value}"
            pg_params.append(param_str)
        return ", ".join(pg_params)

    def apply_syntax_replacements(self, body: str) -> Tuple[str, List[str]]:
        """Apply PL/SQL → PL/pgSQL syntax transformations."""
        translated = body
        warnings = []

        for pattern, replacement in SYNTAX_REPLACEMENTS:
            if re.search(pattern, translated, re.IGNORECASE):
                translated = re.sub(pattern, replacement, translated, flags=re.IGNORECASE)

        return translated, warnings

    def detect_unsupported_constructs(self, body: str) -> List[str]:
        """Scan for Oracle-specific constructs that require manual translation."""
        found = []
        for pattern, description in UNSUPPORTED_PATTERNS:
            if re.search(pattern, body, re.IGNORECASE):
                found.append(description)
        return found

    def translate_procedure(self, proc: PLSQLProcedure) -> Tuple[PostgresFunction, List[str]]:
        """Translate a single Oracle procedure to a PostgreSQL function."""
        logger.info(f"Translating procedure: {proc.schema_name}.{proc.procedure_name}")

        pg_params = self.translate_parameter_list(proc.parameters)
        translated_body, warnings = self.apply_syntax_replacements(proc.body)
        unsupported = self.detect_unsupported_constructs(proc.body)

        # Determine return type
        return_type = "VOID" if proc.object_type == "PROCEDURE" else None

        func_name = proc.procedure_name.lower()
        pg_body = f"""
CREATE OR REPLACE FUNCTION {func_name}({pg_params})
RETURNS {return_type or 'VOID'}
LANGUAGE plpgsql
AS $$
BEGIN
{translated_body}
END;
$$;
""".strip()

        pg_func = PostgresFunction(
            function_name=func_name,
            parameters=pg_params,
            return_type=return_type,
            body=pg_body,
            language="plpgsql",
            source_object=f"{proc.schema_name}.{proc.procedure_name}",
        )
        return pg_func, warnings + unsupported

    def translate_trigger(self, trigger: PLSQLTrigger) -> Tuple[PostgresFunction, PostgresTrigger, List[str]]:
        """Translate an Oracle trigger to a PostgreSQL trigger + trigger function."""
        logger.info(f"Translating trigger: {trigger.schema_name}.{trigger.trigger_name}")

        translated_body, warnings = self.apply_syntax_replacements(trigger.body)
        unsupported = self.detect_unsupported_constructs(trigger.body)

        func_name = f"fn_{trigger.trigger_name.lower()}"
        table_name = trigger.table_name.lower()

        # PostgreSQL requires a separate trigger function
        func_body = f"""
CREATE OR REPLACE FUNCTION {func_name}()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
{translated_body}
    RETURN NEW;
END;
$$;
""".strip()

        pg_func = PostgresFunction(
            function_name=func_name,
            parameters="",
            return_type="TRIGGER",
            body=func_body,
            language="plpgsql",
            source_object=f"{trigger.schema_name}.{trigger.trigger_name}",
        )

        # Parse triggering events
        events = trigger.triggering_event.upper()
        for_each = "FOR EACH ROW" if trigger.for_each_row else "FOR EACH STATEMENT"

        pg_trigger = PostgresTrigger(
            trigger_name=trigger.trigger_name.lower(),
            table_name=table_name,
            trigger_timing=trigger.trigger_type.upper(),
            trigger_event=events,
            function_name=func_name,
            for_each_row=trigger.for_each_row,
            source_trigger=f"{trigger.schema_name}.{trigger.trigger_name}",
        )

        return pg_func, pg_trigger, warnings + unsupported

    def decompose_package(self, package: PLSQLPackage) -> List[PLSQLProcedure]:
        """Decompose an Oracle package into individual procedures/functions.

        PostgreSQL does not have packages, so each procedure becomes a standalone function.
        """
        logger.info(f"Decomposing package: {package.schema_name}.{package.package_name}")
        result = []
        for proc in package.procedures:
            # Prefix function names with package name to avoid collisions
            prefixed_name = f"{package.package_name}_{proc.procedure_name}".lower()
            result.append(PLSQLProcedure(
                schema_name=proc.schema_name,
                object_name=proc.object_name,
                procedure_name=prefixed_name,
                parameters=proc.parameters,
                body=proc.body,
                object_type=proc.object_type,
            ))
        return result

    def translate_all(
        self,
        schema: str,
        procedures: List[PLSQLProcedure],
        triggers: List[PLSQLTrigger],
        packages: List[PLSQLPackage],
    ) -> TranslationResult:
        """Translate all Oracle PL/SQL objects to AlloyDB-compatible PostgreSQL."""
        logger.info(
            f"Translating {len(procedures)} procedures, {len(triggers)} triggers, "
            f"{len(packages)} packages from schema {schema}"
        )

        all_functions = []
        all_triggers = []
        all_warnings = []
        all_unsupported = []

        # Decompose packages into individual procedures
        for pkg in packages:
            procedures = procedures + self.decompose_package(pkg)

        # Translate procedures
        for proc in procedures:
            pg_func, issues = self.translate_procedure(proc)
            all_functions.append(pg_func)
            all_warnings.extend([w for w in issues if w not in all_unsupported])

        # Translate triggers
        for trigger in triggers:
            pg_func, pg_trigger, issues = self.translate_trigger(trigger)
            all_functions.append(pg_func)
            all_triggers.append(pg_trigger)
            all_warnings.extend([w for w in issues if w not in all_unsupported])

        # Separate warnings from unsupported constructs
        unsupported_descriptions = [desc for _, desc in UNSUPPORTED_PATTERNS]
        final_unsupported = [w for w in all_warnings if w in unsupported_descriptions]
        final_warnings = [w for w in all_warnings if w not in unsupported_descriptions]

        return TranslationResult(
            source_schema=schema,
            functions=all_functions,
            triggers=all_triggers,
            warnings=list(set(final_warnings)),
            unsupported_constructs=list(set(final_unsupported)),
        )
