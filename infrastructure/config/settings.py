"""OracleForge configuration management using Pydantic Settings.

Loads configuration from (in priority order):
1. CLI flag overrides
2. Environment variables with ORACLEFORGE_ prefix
3. oracleforge.yaml project config file
4. Built-in defaults
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OracleSettings(BaseSettings):
    """Oracle EBS connection settings."""
    connection_string: str = Field(
        default="oracle+cx_oracle://apps:apps@localhost:1521/EBSDB",
        description="SQLAlchemy connection string for Oracle EBS",
    )
    schema_name: str = Field(default="APPS", description="Default Oracle schema")

    model_config = SettingsConfigDict(env_prefix="ORACLEFORGE_ORACLE_")


class GCPSettings(BaseSettings):
    """Google Cloud Platform settings."""
    project_id: str = Field(default="oracleforge-dev", description="GCP project ID")
    region: str = Field(default="us-central1", description="Default GCP region")
    bronze_dataset: str = Field(default="bronze", description="Bronze layer dataset")
    silver_dataset: str = Field(default="silver", description="Silver layer dataset")
    gold_dataset: str = Field(default="gold", description="Gold layer dataset")

    model_config = SettingsConfigDict(env_prefix="ORACLEFORGE_GCP_")


class AlloyDBSettings(BaseSettings):
    """AlloyDB Omni connection settings."""
    connection_string: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/oracleforge",
        description="SQLAlchemy connection string for AlloyDB",
    )

    model_config = SettingsConfigDict(env_prefix="ORACLEFORGE_ALLOYDB_")


class DbtSettings(BaseSettings):
    """dbt project generation settings."""
    output_dir: str = Field(default="./dbt_project", description="dbt output directory")
    project_name: str = Field(default="oracleforge_dbt", description="dbt project name")

    model_config = SettingsConfigDict(env_prefix="ORACLEFORGE_DBT_")


class LoggingSettings(BaseSettings):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format: json or text")
    log_file: Optional[str] = Field(default=None, description="Optional log file path")

    model_config = SettingsConfigDict(env_prefix="ORACLEFORGE_LOG_")


class OracleForgeSettings(BaseSettings):
    """Root settings for OracleForge.

    Combines all sub-settings into a single configuration object.
    """
    oracle: OracleSettings = Field(default_factory=OracleSettings)
    gcp: GCPSettings = Field(default_factory=GCPSettings)
    alloydb: AlloyDBSettings = Field(default_factory=AlloyDBSettings)
    dbt: DbtSettings = Field(default_factory=DbtSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    use_mock: bool = Field(
        default=True,
        description="Use mock adapters instead of real Oracle/GCP connections",
    )

    model_config = SettingsConfigDict(
        env_prefix="ORACLEFORGE_",
        yaml_file="oracleforge.yaml",
        yaml_file_encoding="utf-8",
        extra="ignore",
    )
