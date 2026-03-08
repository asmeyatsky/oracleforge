from typing import Protocol, List, Dict, Any, Optional
from domain.entities.gl import GLBalance, JournalEntry
from domain.entities.ap import Invoice
from domain.entities.hcm import Employee

class GCPTargetPort(Protocol):
    """Port for interacting with Google Cloud Platform target services."""

    async def load_to_bigquery(self, dataset: str, table: str, data: List[Dict[str, Any]]) -> bool:
        """Load flattened data into BigQuery tables (Bronze/Silver/Gold layers)."""
        ...

    async def upload_to_gcs(self, bucket: str, path: str, data: bytes) -> str:
        """Upload raw Oracle export files to Google Cloud Storage."""
        ...

    async def get_bq_data(self, query: str) -> List[Dict[str, Any]]:
        """Fetch data from BigQuery for analytical purposes."""
        ...

    async def trigger_datastream_cdc(self, source_name: str, target_name: str) -> bool:
        """Trigger or manage Google Cloud Datastream CDC jobs."""
        ...

    async def provision_bq_dataset(self, dataset_id: str, location: str) -> bool:
        """Provision a BigQuery dataset with region-specific (Dammam, Doha) lockdown."""
        ...
