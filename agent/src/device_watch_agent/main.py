"""Native agent process entry point."""

from __future__ import annotations

import asyncio
import logging
import signal

from device_watch_agent.collectors.registry import CollectorRegistry
from device_watch_agent.config import load_settings
from device_watch_agent.lifecycle import AgentRuntime
from device_watch_agent.logging import setup_logging

logger = logging.getLogger(__name__)


def _install_signal_handlers(
    stop_event: asyncio.Event,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Install ordinary termination handlers where the platform permits it."""

    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, stop_event.set)
        except (NotImplementedError, RuntimeError, ValueError):
            logger.debug("signal handler unavailable", extra={"signal": signum})


async def _run() -> None:
    settings = load_settings()
    registry = CollectorRegistry()
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    _install_signal_handlers(stop_event, loop)
    await AgentRuntime(settings.interval_seconds, registry).run(stop_event)


def main() -> int:
    """Run the empty Stage 1 runtime and return a process status."""

    setup_logging()
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        return 0
    return 0


__all__ = ["main"]
