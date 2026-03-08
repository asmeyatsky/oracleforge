from typing import Protocol, List
from domain.events.migration_events import MigrationEvent


class EventBusPort(Protocol):
    """Port for publishing domain events."""

    async def publish(self, event: MigrationEvent) -> None:
        """Publish a single domain event."""
        ...

    async def publish_batch(self, events: List[MigrationEvent]) -> None:
        """Publish multiple domain events."""
        ...
