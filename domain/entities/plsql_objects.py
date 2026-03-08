from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass(frozen=True)
class PLSQLParameter:
    """A parameter in a PL/SQL procedure or function."""
    name: str
    data_type: str  # Oracle type: VARCHAR2, NUMBER, DATE, etc.
    direction: str = "IN"  # IN, OUT, IN OUT
    default_value: Optional[str] = None


@dataclass(frozen=True)
class PLSQLProcedure:
    """Represents an Oracle PL/SQL stored procedure."""
    schema_name: str
    object_name: str
    procedure_name: str
    parameters: List[PLSQLParameter] = field(default_factory=list)
    body: str = ""
    object_type: str = "PROCEDURE"  # PROCEDURE, FUNCTION


@dataclass(frozen=True)
class PLSQLTrigger:
    """Represents an Oracle PL/SQL trigger."""
    schema_name: str
    trigger_name: str
    table_name: str
    trigger_type: str  # BEFORE, AFTER, INSTEAD OF
    triggering_event: str  # INSERT, UPDATE, DELETE, or combinations
    body: str = ""
    when_clause: Optional[str] = None
    for_each_row: bool = True


@dataclass(frozen=True)
class PLSQLPackage:
    """Represents an Oracle PL/SQL package (spec + body)."""
    schema_name: str
    package_name: str
    procedures: List[PLSQLProcedure] = field(default_factory=list)
    spec_body: str = ""
    package_body: str = ""


@dataclass(frozen=True)
class PostgresFunction:
    """The result of translating an Oracle PL/SQL object to PostgreSQL/AlloyDB."""
    function_name: str
    parameters: str  # PostgreSQL parameter list
    return_type: Optional[str] = None
    body: str = ""
    language: str = "plpgsql"
    source_object: str = ""  # Original Oracle object name


@dataclass(frozen=True)
class PostgresTrigger:
    """The result of translating an Oracle trigger to PostgreSQL/AlloyDB."""
    trigger_name: str
    table_name: str
    trigger_timing: str  # BEFORE, AFTER
    trigger_event: str  # INSERT, UPDATE, DELETE
    function_name: str  # Reference to trigger function
    for_each_row: bool = True
    source_trigger: str = ""  # Original Oracle trigger name


@dataclass(frozen=True)
class TranslationResult:
    """Complete result of translating Oracle PL/SQL to AlloyDB-compatible PostgreSQL."""
    source_schema: str
    functions: List[PostgresFunction] = field(default_factory=list)
    triggers: List[PostgresTrigger] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    unsupported_constructs: List[str] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def has_unsupported(self) -> bool:
        return len(self.unsupported_constructs) > 0

    @property
    def total_objects(self) -> int:
        return len(self.functions) + len(self.triggers)
