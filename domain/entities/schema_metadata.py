from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass(frozen=True)
class ColumnMetadata:
    """Metadata for a single Oracle table column."""
    column_name: str
    data_type: str  # VARCHAR2, NUMBER, DATE, CLOB, etc.
    nullable: bool = True
    data_length: Optional[int] = None
    data_precision: Optional[int] = None
    data_scale: Optional[int] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    fk_target_table: Optional[str] = None
    fk_target_column: Optional[str] = None


@dataclass(frozen=True)
class FlexfieldInfo:
    """Represents a Key Flexfield (KFF) or Descriptive Flexfield (DFF) column group."""
    flexfield_type: str  # "KFF" or "DFF"
    table_name: str
    columns: List[str]  # e.g., ["SEGMENT1", "SEGMENT2", ...] or ["ATTRIBUTE1", ...]
    structure_name: Optional[str] = None  # e.g., "Accounting Flexfield"


@dataclass(frozen=True)
class TableClassification:
    """Classification result for an Oracle table from the SIE."""
    table_name: str
    module: str  # "GL", "AP", "HCM", "UNKNOWN"
    table_type: str  # "transactional", "master_data", "reference", "setup", "interface"
    columns: List[ColumnMetadata] = field(default_factory=list)
    flexfields: List[FlexfieldInfo] = field(default_factory=list)
    primary_key_columns: List[str] = field(default_factory=list)
    estimated_row_count: Optional[int] = None
    description: Optional[str] = None

    @property
    def has_flexfields(self) -> bool:
        return len(self.flexfields) > 0

    @property
    def segment_columns(self) -> List[str]:
        """All SEGMENT columns across all KFFs."""
        cols = []
        for ff in self.flexfields:
            if ff.flexfield_type == "KFF":
                cols.extend(ff.columns)
        return cols

    @property
    def attribute_columns(self) -> List[str]:
        """All ATTRIBUTE columns across all DFFs."""
        cols = []
        for ff in self.flexfields:
            if ff.flexfield_type == "DFF":
                cols.extend(ff.columns)
        return cols


@dataclass(frozen=True)
class DbtModelSpec:
    """Specification for a generated dbt model."""
    model_name: str
    source_table: str
    module: str
    layer: str  # "staging", "intermediate", "mart"
    sql_content: str
    yaml_content: str
    description: str = ""
    materialization: str = "view"  # "view", "table", "incremental"
    tags: List[str] = field(default_factory=list)
