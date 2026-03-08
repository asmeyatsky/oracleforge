import logging
from typing import List
from domain.ports.event_ports import EventBusPort
from domain.events.migration_events import MigrationEvent

logger = logging.getLogger(__name__)


class LoggingEventBus(EventBusPort):
    """Event bus adapter that logs events to the structured logging pipeline.

    Initial implementation for observability. Can be swapped for
    Google Pub/Sub or Cloud Tasks in production.
    """

    def __init__(self):
        self.published_events: List[MigrationEvent] = []

    async def publish(self, event: MigrationEvent) -> None:
        logger.info(
            f"Event: {type(event).__name__} | module={event.module} "
            f"period={event.period_name} org={event.org_id}"
        )
        self.published_events.append(event)

    async def publish_batch(self, events: List[MigrationEvent]) -> None:
        for event in events:
            await self.publish(event)
