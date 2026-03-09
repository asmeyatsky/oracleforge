"""Mock CDC adapter for testing and demos.

Implements CDCPipelinePort entirely in-memory, simulating stream
creation, status tracking, pause/resume, and deletion.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List

from domain.entities.cdc import CDCStreamConfig, CDCStreamStatus
from domain.ports.cdc_ports import CDCPipelinePort

logger = logging.getLogger(__name__)


class MockCDCAdapter(CDCPipelinePort):
    """In-memory mock implementation of CDCPipelinePort.

    Tracks streams in a dictionary keyed by stream_name.
    """

    def __init__(self):
        self._streams: Dict[str, CDCStreamConfig] = {}
        self._statuses: Dict[str, CDCStreamStatus] = {}

    async def create_stream(self, config: CDCStreamConfig) -> bool:
        logger.info(f"MOCK CDC: Creating stream '{config.stream_name}'")
        self._streams[config.stream_name] = config
        self._statuses[config.stream_name] = CDCStreamStatus(
            stream_name=config.stream_name,
            status="NOT_STARTED",
            tables_synced=0,
            total_tables=len(config.source_tables),
        )
        return True

    async def get_stream_status(self, stream_name: str) -> CDCStreamStatus:
        logger.info(f"MOCK CDC: Getting status for '{stream_name}'")
        if stream_name not in self._statuses:
            return CDCStreamStatus(
                stream_name=stream_name,
                status="NOT_STARTED",
            )

        current = self._statuses[stream_name]

        # Simulate progress: if stream was started (RUNNING), report synced tables
        if current.status == "RUNNING":
            synced = min(current.tables_synced + 1, current.total_tables)
            updated = CDCStreamStatus(
                stream_name=current.stream_name,
                status="RUNNING",
                tables_synced=synced,
                total_tables=current.total_tables,
                last_sync_time=datetime.now(timezone.utc),
                rows_synced=current.rows_synced + 100,
            )
            self._statuses[stream_name] = updated
            return updated

        return current

    async def pause_stream(self, stream_name: str) -> bool:
        logger.info(f"MOCK CDC: Pausing stream '{stream_name}'")
        if stream_name not in self._statuses:
            return False
        current = self._statuses[stream_name]
        self._statuses[stream_name] = CDCStreamStatus(
            stream_name=current.stream_name,
            status="PAUSED",
            tables_synced=current.tables_synced,
            total_tables=current.total_tables,
            last_sync_time=current.last_sync_time,
            rows_synced=current.rows_synced,
        )
        return True

    async def resume_stream(self, stream_name: str) -> bool:
        logger.info(f"MOCK CDC: Resuming stream '{stream_name}'")
        if stream_name not in self._statuses:
            return False
        current = self._statuses[stream_name]
        self._statuses[stream_name] = CDCStreamStatus(
            stream_name=current.stream_name,
            status="RUNNING",
            tables_synced=current.tables_synced,
            total_tables=current.total_tables,
            last_sync_time=current.last_sync_time,
            rows_synced=current.rows_synced,
        )
        return True

    async def delete_stream(self, stream_name: str) -> bool:
        logger.info(f"MOCK CDC: Deleting stream '{stream_name}'")
        if stream_name not in self._streams:
            return False
        del self._streams[stream_name]
        del self._statuses[stream_name]
        return True

    async def list_streams(self) -> List[CDCStreamStatus]:
        logger.info(f"MOCK CDC: Listing {len(self._statuses)} streams")
        return list(self._statuses.values())
