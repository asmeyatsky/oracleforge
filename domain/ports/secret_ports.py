from typing import Protocol, Dict, Any, Optional

class SecretManagerPort(Protocol):
    """Port for abstracting secret and credential management (e.g., GCP Secret Manager)."""

    async def get_secret(self, secret_name: str) -> str:
        """Fetch a secret value by its name."""
        ...

    async def get_db_credentials(self, db_instance: str) -> Dict[str, Any]:
        """Fetch database credentials for a specific instance."""
        ...

    async def create_secret(self, secret_name: str, value: str) -> bool:
        """Create or update a secret value."""
        ...
