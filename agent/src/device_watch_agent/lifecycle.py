"""Signal-aware, empty-registry agent lifecycle."""

from __future__ import annotations

import asyncio
import logging

from device_watch_agent.collectors.registry import CollectorRegistry

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Wait between future collection intervals without collecting in Stage 1."""

    def __init__(self, interval_seconds: float, registry: CollectorRegistry) -> None:
        self.interval_seconds = interval_seconds
        self.registry = registry

    async def run(self, stop_event: asyncio.Event) -> None:
        """Wait efficiently until a stop is requested or cancellation occurs."""

        logger.info("agent started with %d collectors", len(self.registry))
        try:
            while not stop_event.is_set():
                try:
                    await asyncio.wait_for(
                        stop_event.wait(), timeout=self.interval_seconds
                    )
                except TimeoutError:
                    continue
        except asyncio.CancelledError:
            logger.info("agent cancelled")
            raise
        finally:
            logger.info("agent stopped")


__all__ = ["AgentRuntime"]
