"""OracleForge bootstrap — single entry point for initializing the application.

Loads settings, configures logging, and wires the DI container.
"""

import logging
import sys
from typing import Optional
from infrastructure.config.settings import OracleForgeSettings
from infrastructure.config.dependency_injection import Container


logger = logging.getLogger(__name__)


def configure_logging(settings: OracleForgeSettings) -> None:
    """Configure structured logging based on settings."""
    log_level = getattr(logging, settings.logging.level.upper(), logging.INFO)

    handlers = [logging.StreamHandler(sys.stderr)]
    if settings.logging.log_file:
        handlers.append(logging.FileHandler(settings.logging.log_file))

    if settings.logging.format == "json":
        fmt = '{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'
    else:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    logging.basicConfig(
        level=log_level,
        format=fmt,
        handlers=handlers,
        force=True,
    )


def create_container(settings: Optional[OracleForgeSettings] = None) -> Container:
    """Create and wire the DI container from settings.

    Args:
        settings: Optional pre-built settings. If None, loads from
                  environment/yaml automatically.

    Returns:
        Fully wired Container ready for use.
    """
    if settings is None:
        settings = OracleForgeSettings()

    configure_logging(settings)
    logger.info("Bootstrapping OracleForge container")

    container = Container()

    # Wire configuration into the container
    container.config.from_dict({
        "use_mock_oracle": "mock" if settings.use_mock else "real",
        "use_mock_gcp": "mock" if settings.use_mock else "real",
        "use_mock_reconciliation": "mock" if settings.use_mock else "real",
        "oracle": {
            "connection_string": settings.oracle.connection_string,
            "schema_name": settings.oracle.schema_name,
        },
        "gcp": {
            "project_id": settings.gcp.project_id,
            "region": settings.gcp.region,
            "bronze_dataset": settings.gcp.bronze_dataset,
            "silver_dataset": settings.gcp.silver_dataset,
            "gold_dataset": settings.gcp.gold_dataset,
        },
        "alloydb": {
            "connection_string": settings.alloydb.connection_string,
        },
        "dbt": {
            "output_dir": settings.dbt.output_dir,
        },
    })

    logger.info(
        f"Container initialized (mock={settings.use_mock}, "
        f"project={settings.gcp.project_id}, region={settings.gcp.region})"
    )
    return container
