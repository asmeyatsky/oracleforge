import logging
from typing import List, Dict, Any
from domain.ports.gcp_ports import GCPTargetPort

logger = logging.getLogger(__name__)


class MockGCPAdapter(GCPTargetPort):
    """Mock GCP adapter that logs operations without requiring GCP credentials.

    Tracks loaded data in memory for verification in tests and demos.
    """

    def __init__(self):
        self.loaded_data: Dict[str, List[Dict[str, Any]]] = {}
        self.uploaded_files: List[str] = []
        self.provisioned_datasets: List[str] = []

    async def load_to_bigquery(self, dataset: str, table: str, data: List[Dict[str, Any]]) -> bool:
        key = f"{dataset}.{table}"
        logger.info(f"MOCK: Loading {len(data)} rows to BigQuery {key}")
        self.loaded_data.setdefault(key, []).extend(data)
        return True

    async def upload_to_gcs(self, bucket: str, path: str, data: bytes) -> str:
        uri = f"gs://{bucket}/{path}"
        logger.info(f"MOCK: Uploading {len(data)} bytes to {uri}")
        self.uploaded_files.append(uri)
        return uri

    async def get_bq_data(self, query: str) -> List[Dict[str, Any]]:
        logger.info(f"MOCK: Executing BigQuery query: {query[:80]}...")
        # Return data from in-memory store if available
        return []

    async def trigger_datastream_cdc(self, source_name: str, target_name: str) -> bool:
        logger.info(f"MOCK: Triggering Datastream CDC {source_name} -> {target_name}")
        return True

    async def provision_bq_dataset(self, dataset_id: str, location: str) -> bool:
        logger.info(f"MOCK: Provisioning BigQuery dataset {dataset_id} in {location}")
        self.provisioned_datasets.append(f"{dataset_id}@{location}")
        return True
