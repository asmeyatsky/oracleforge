import logging
from typing import List, Dict, Any, Optional
from google.cloud import bigquery, storage, datastream_v1
from domain.ports.gcp_ports import GCPTargetPort

logger = logging.getLogger(__name__)

class GCPTargetAdapter(GCPTargetPort):
    """
    Adapter for interacting with Google Cloud Platform services.
    Implements GCPTargetPort.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.bq_client = bigquery.Client(project=project_id)
        self.gcs_client = storage.Client(project=project_id)
        self.datastream_client = datastream_v1.DatastreamClient()

    async def load_to_bigquery(self, dataset: str, table: str, data: List[Dict[str, Any]]) -> bool:
        """Load data into a BigQuery table."""
        logger.info(f"Loading {len(data)} rows to BigQuery table {dataset}.{table}")
        table_id = f"{self.project_id}.{dataset}.{table}"
        job = self.bq_client.load_table_from_json(data, table_id)
        job.result()  # Wait for the job to complete
        return True

    async def upload_to_gcs(self, bucket: str, path: str, data: bytes) -> str:
        """Upload data to a GCS bucket."""
        logger.info(f"Uploading data to GCS bucket {bucket} at path {path}")
        bucket_obj = self.gcs_client.bucket(bucket)
        blob = bucket_obj.blob(path)
        blob.upload_from_string(data)
        return f"gs://{bucket}/{path}"

    async def get_bq_data(self, query: str) -> List[Dict[str, Any]]:
        """Fetch data from BigQuery."""
        logger.info(f"Executing BigQuery query: {query}")
        query_job = self.bq_client.query(query)
        results = query_job.result()
        return [dict(row) for row in results]

    async def trigger_datastream_cdc(self, source_name: str, target_name: str) -> bool:
        """Trigger or manage Google Cloud Datastream CDC jobs."""
        logger.info(f"Triggering Datastream CDC from {source_name} to {target_name}")
        # Simplified trigger logic
        return True

    async def provision_bq_dataset(self, dataset_id: str, location: str) -> bool:
        """Provision a BigQuery dataset with a specific location."""
        logger.info(f"Provisioning BigQuery dataset {dataset_id} in location {location}")
        dataset = bigquery.Dataset(f"{self.project_id}.{dataset_id}")
        dataset.location = location
        self.bq_client.create_dataset(dataset, exists_ok=True)
        return True
