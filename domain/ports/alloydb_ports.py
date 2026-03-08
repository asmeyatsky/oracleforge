from typing import Protocol, List, Dict, Any, Optional
from domain.entities.plsql_objects import (
    PLSQLProcedure,
    PLSQLTrigger,
    PLSQLPackage,
    TranslationResult,
)


class AlloyDBPort(Protocol):
    """Port for managing AlloyDB Omni as a compatibility layer for Oracle workloads."""

    async def extract_plsql_objects(self, schema: str) -> Dict[str, Any]:
        """Extract PL/SQL procedures, functions, triggers, and packages from Oracle."""
        ...

    async def translate_to_postgresql(
        self,
        procedures: List[PLSQLProcedure],
        triggers: List[PLSQLTrigger],
        packages: List[PLSQLPackage],
    ) -> TranslationResult:
        """Translate Oracle PL/SQL objects to AlloyDB-compatible PostgreSQL."""
        ...

    async def deploy_to_alloydb(self, result: TranslationResult, target_schema: str) -> bool:
        """Deploy translated PostgreSQL functions and triggers to AlloyDB."""
        ...

    async def validate_translation(self, result: TranslationResult) -> List[str]:
        """Validate translated PostgreSQL code for syntax and compatibility issues."""
        ...
