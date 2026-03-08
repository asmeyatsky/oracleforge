import logging
import json
from typing import Dict, Any, Optional
from google.cloud import secretmanager
from domain.ports.secret_ports import SecretManagerPort

logger = logging.getLogger(__name__)

class GCPSecretAdapter(SecretManagerPort):
    """
    Adapter for interacting with Google Cloud Secret Manager.
    Implements SecretManagerPort.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()

    async def get_secret(self, secret_name: str) -> str:
        """Fetch a secret value from GCP Secret Manager."""
        logger.info(f"Fetching secret: {secret_name}")
        name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
        response = self.client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")

    async def get_db_credentials(self, db_instance: str) -> Dict[str, Any]:
        """Fetch database credentials for a specific instance."""
        secret_value = await self.get_secret(f"oracle-db-{db_instance}")
        return json.loads(secret_value)

    async def create_secret(self, secret_name: str, value: str) -> bool:
        """Create or update a secret value in GCP Secret Manager."""
        logger.info(f"Creating/updating secret: {secret_name}")
        parent = f"projects/{self.project_id}"
        
        # Check if secret exists, if not create it
        try:
            self.client.get_secret(request={"name": f"{parent}/secrets/{secret_name}"})
        except Exception:
            self.client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_name,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
            
        # Add new version
        self.client.add_secret_version(
            request={
                "parent": f"{parent}/secrets/{secret_name}",
                "payload": {"data": value.encode("UTF-8")},
            }
        )
        return True
