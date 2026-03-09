"""OracleForge Real-world Validation Script.

Checks connectivity to Oracle and GCP services if 'real' mode is enabled.
"""

import asyncio
import logging
import os
import sys
from infrastructure.config.bootstrap import create_container
from infrastructure.config.settings import OracleForgeSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("oracleforge-validation")

async def validate_environment():
    settings = OracleForgeSettings()
    
    print(f"\n--- OracleForge Validation ({'MOCK' if settings.use_mock else 'REAL'} mode) ---\n")
    
    if settings.use_mock:
        logger.info("Running in MOCK mode. Connectivity checks will use mock adapters.")
    else:
        logger.info("Running in REAL mode. Validating actual service connectivity.")
        
        # Check GCP Env
        if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            logger.warning("GOOGLE_APPLICATION_CREDENTIALS not set. Auth might fail.")

    container = create_container(settings)
    
    # 1. Oracle Connectivity
    oracle = container.oracle_adapter()
    try:
        logger.info("Testing Oracle connection and metadata extraction...")
        metadata = await oracle.get_schema_metadata()
        table_count = len(metadata.get("tables", []))
        logger.info(f"OK: Oracle connected. Found {table_count} tables.")
    except Exception as e:
        logger.error(f"FAIL: Oracle connectivity failed: {e}")

    # 2. GCP Secret Manager
    secrets = container.secret_adapter()
    try:
        logger.info(f"Testing GCP Secret Manager access (Project: {settings.gcp.project_id})...")
        # Just try to list or get a non-existent secret to check API access
        try:
            await secrets.get_secret("health-check")
        except Exception as e:
            if "NOT_FOUND" in str(e) or "404" in str(e):
                logger.info("OK: Secret Manager API accessible (Secret 'health-check' not found as expected).")
            else:
                raise e
    except Exception as e:
        logger.error(f"FAIL: Secret Manager connectivity failed: {e}")

    # 3. BigQuery / GCP Storage
    gcp = container.gcp_adapter()
    try:
        logger.info(f"Testing BigQuery access (Dataset: {settings.gcp.bronze_dataset})...")
        # In mock mode this always succeeds. In real mode it checks BQ.
        await gcp.load_to_bigquery(settings.gcp.bronze_dataset, "health_check_table", [{"status": "ok"}])
        logger.info("OK: BigQuery write successful.")
    except Exception as e:
        logger.error(f"FAIL: BigQuery connectivity failed: {e}")

    # 4. Vertex AI
    ai = container.vertex_ai_adapter()
    try:
        logger.info("Testing Vertex AI API connectivity...")
        # Simple prompt
        await ai.generate_insight("Hello", "Return 'OK'")
        logger.info("OK: Vertex AI connected.")
    except Exception as e:
        logger.error(f"FAIL: Vertex AI connectivity failed: {e}")

    print("\n--- Validation Summary ---\n")

if __name__ == "__main__":
    asyncio.run(validate_environment())
