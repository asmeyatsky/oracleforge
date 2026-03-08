from typing import Protocol, List
from domain.entities.schema_metadata import TableClassification, DbtModelSpec


class CodeGeneratorPort(Protocol):
    """Port for generating GCP-native SQL models from Oracle schema metadata."""

    async def generate_staging_model(self, table: TableClassification) -> DbtModelSpec:
        """Generate a dbt staging model SQL and YAML for a classified Oracle table."""
        ...

    async def generate_intermediate_model(self, table: TableClassification) -> DbtModelSpec:
        """Generate a dbt intermediate model with business logic transformations."""
        ...

    async def generate_mart_model(self, tables: List[TableClassification]) -> DbtModelSpec:
        """Generate a dbt mart model joining related tables for analytics."""
        ...

    async def write_model_files(self, model: DbtModelSpec, output_dir: str) -> List[str]:
        """Write generated SQL and YAML files to disk. Returns list of file paths."""
        ...
