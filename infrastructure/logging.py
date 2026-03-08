import logging
import sys

def setup_logging(level: str = "INFO"):
    """
    Configures standard logging for OracleForge components.
    Ensures output is suitable for both CLI and MCP server integration.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Suppress verbose logs from third-party libs
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    return logging.getLogger("oracleforge")

logger = setup_logging()
