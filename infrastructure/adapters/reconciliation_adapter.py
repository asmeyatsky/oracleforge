import logging
from typing import List
from decimal import Decimal
from sqlalchemy import create_engine, text
from google.cloud import bigquery
from domain.ports.reconciliation_ports import ReconciliationPort
from domain.value_objects.common import MultiOrgContext

logger = logging.getLogger(__name__)


class ReconciliationAdapter(ReconciliationPort):
    """Adapter that queries both Oracle and BigQuery for reconciliation data."""

    def __init__(self, oracle_connection_string: str, gcp_project_id: str):
        self.oracle_engine = create_engine(oracle_connection_string)
        self.bq_client = bigquery.Client(project=gcp_project_id)
        self.gcp_project_id = gcp_project_id

    async def get_source_row_count(self, table: str, context: MultiOrgContext) -> int:
        logger.info(f"Counting rows in Oracle table {table} for org {context.org_id}")
        with self.oracle_engine.connect() as conn:
            result = conn.execute(
                text(f"SELECT COUNT(*) AS cnt FROM {table} WHERE org_id = :org_id"),
                {"org_id": context.org_id},
            )
            row = result.fetchone()
            return int(row[0]) if row else 0

    async def get_target_row_count(self, dataset: str, table: str) -> int:
        logger.info(f"Counting rows in BigQuery table {dataset}.{table}")
        query = f"SELECT COUNT(*) AS cnt FROM `{self.gcp_project_id}.{dataset}.{table}`"
        result = self.bq_client.query(query).result()
        for row in result:
            return int(row.cnt)
        return 0

    async def get_source_checksum(
        self, table: str, columns: List[str], context: MultiOrgContext
    ) -> str:
        col_expr = " || ".join(
            [f"NVL(TO_CHAR({c}), '')" for c in columns]
        )
        query = (
            f"SELECT ORA_HASH(LISTAGG({col_expr}, ',') WITHIN GROUP (ORDER BY ROWID)) "
            f"AS chk FROM {table} WHERE org_id = :org_id"
        )
        logger.info(f"Computing checksum on Oracle {table}")
        with self.oracle_engine.connect() as conn:
            result = conn.execute(text(query), {"org_id": context.org_id})
            row = result.fetchone()
            return str(row[0]) if row else ""

    async def get_target_checksum(
        self, dataset: str, table: str, columns: List[str]
    ) -> str:
        col_expr = " || ".join(
            [f"COALESCE(CAST({c} AS STRING), '')" for c in columns]
        )
        query = (
            f"SELECT FARM_FINGERPRINT(STRING_AGG({col_expr}, ',' ORDER BY _row_id)) "
            f"AS chk FROM `{self.gcp_project_id}.{dataset}.{table}`"
        )
        logger.info(f"Computing checksum on BigQuery {dataset}.{table}")
        result = self.bq_client.query(query).result()
        for row in result:
            return str(row.chk)
        return ""

    async def get_source_aggregate(
        self, table: str, column: str, context: MultiOrgContext
    ) -> Decimal:
        logger.info(f"Aggregating Oracle {table}.{column}")
        with self.oracle_engine.connect() as conn:
            result = conn.execute(
                text(
                    f"SELECT NVL(SUM({column}), 0) AS total FROM {table} "
                    f"WHERE org_id = :org_id"
                ),
                {"org_id": context.org_id},
            )
            row = result.fetchone()
            return Decimal(str(row[0])) if row else Decimal("0")

    async def get_target_aggregate(
        self, dataset: str, table: str, column: str
    ) -> Decimal:
        logger.info(f"Aggregating BigQuery {dataset}.{table}.{column}")
        query = (
            f"SELECT COALESCE(SUM({column}), 0) AS total "
            f"FROM `{self.gcp_project_id}.{dataset}.{table}`"
        )
        result = self.bq_client.query(query).result()
        for row in result:
            return Decimal(str(row.total))
        return Decimal("0")
