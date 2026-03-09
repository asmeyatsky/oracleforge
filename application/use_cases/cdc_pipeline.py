"""CDC Pipeline Use Case — orchestrates CDC stream lifecycle.

Coordinates between the CDCPipelinePort (Datastream / mock), GCPTargetPort
(BigQuery dataset provisioning and CDC trigger), and the EventBus for
observability.
"""

import logging
from typing import List

from domain.entities.cdc import CDCStreamStatus
from domain.ports.cdc_ports import CDCPipelinePort
from domain.ports.event_ports import EventBusPort
from domain.ports.gcp_ports import GCPTargetPort
from domain.services.cdc_service import CDCOrchestrationService

logger = logging.getLogger(__name__)


class CDCPipelineUseCase:
    """Application-level use case for managing CDC replication streams."""

    def __init__(
        self,
        cdc_port: CDCPipelinePort,
        gcp_port: GCPTargetPort,
        event_bus: EventBusPort,
    ):
        self.cdc_port = cdc_port
        self.gcp_port = gcp_port
        self.event_bus = event_bus
        self.cdc_service = CDCOrchestrationService()

    async def start_cdc(
        self,
        module: str,
        source_schema: str,
        target_dataset: str,
        target_project: str,
    ) -> CDCStreamStatus:
        """Build a CDC config for *module*, create the stream, trigger Datastream,
        and return the initial stream status.

        Raises ValueError if the module is unknown or the config is invalid.
        """
        # 1. Build and validate configuration
        config = self.cdc_service.build_stream_config(
            module, source_schema, target_dataset, target_project
        )
        errors = self.cdc_service.validate_stream_config(config)
        if errors:
            raise ValueError(f"Invalid CDC config: {'; '.join(errors)}")

        logger.info(
            f"Starting CDC for module={module} stream={config.stream_name} "
            f"tables={len(config.source_tables)}"
        )

        # 2. Create the stream via the CDC port
        await self.cdc_port.create_stream(config)

        # 3. Trigger Datastream via the GCP port
        await self.gcp_port.trigger_datastream_cdc(
            source_name=config.source_schema,
            target_name=config.target_dataset,
        )

        # 4. Resume (start) the stream so it transitions to RUNNING
        await self.cdc_port.resume_stream(config.stream_name)

        # 5. Return the current status
        status = await self.cdc_port.get_stream_status(config.stream_name)
        logger.info(f"CDC stream '{config.stream_name}' status: {status.status}")
        return status

    async def check_health(self, stream_name: str) -> CDCStreamStatus:
        """Return the current status of a CDC stream and log health assessment."""
        status = await self.cdc_port.get_stream_status(stream_name)
        healthy = self.cdc_service.is_stream_healthy(status)
        progress = self.cdc_service.calculate_sync_progress(status)
        logger.info(
            f"CDC health check: stream={stream_name} status={status.status} "
            f"healthy={healthy} progress={progress:.0%}"
        )
        return status

    async def pause_cdc(self, stream_name: str) -> bool:
        """Pause a running CDC stream."""
        logger.info(f"Pausing CDC stream '{stream_name}'")
        return await self.cdc_port.pause_stream(stream_name)

    async def resume_cdc(self, stream_name: str) -> bool:
        """Resume a paused CDC stream."""
        logger.info(f"Resuming CDC stream '{stream_name}'")
        return await self.cdc_port.resume_stream(stream_name)

    async def list_all_streams(self) -> List[CDCStreamStatus]:
        """List all CDC streams with their current status."""
        streams = await self.cdc_port.list_streams()
        logger.info(f"Listed {len(streams)} CDC streams")
        return streams
