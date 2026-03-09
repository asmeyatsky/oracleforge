"""Protocol-based port for CDC pipeline operations.

Defines the contract that any CDC adapter (Datastream, Debezium, mock, etc.)
must satisfy. Pure domain — no infrastructure imports.
"""

from typing import List, Protocol

from domain.entities.cdc import CDCStreamConfig, CDCStreamStatus


class CDCPipelinePort(Protocol):
    """Port for managing CDC replication streams."""

    async def create_stream(self, config: CDCStreamConfig) -> bool:
        """Create a new CDC stream from the given configuration."""
        ...

    async def get_stream_status(self, stream_name: str) -> CDCStreamStatus:
        """Return the current status of a named CDC stream."""
        ...

    async def pause_stream(self, stream_name: str) -> bool:
        """Pause a running CDC stream."""
        ...

    async def resume_stream(self, stream_name: str) -> bool:
        """Resume a paused CDC stream."""
        ...

    async def delete_stream(self, stream_name: str) -> bool:
        """Delete a CDC stream permanently."""
        ...

    async def list_streams(self) -> List[CDCStreamStatus]:
        """List all CDC streams with their current status."""
        ...
