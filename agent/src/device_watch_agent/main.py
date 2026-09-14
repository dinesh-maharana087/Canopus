"""Native agent process entry point."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal

from device_watch_agent.collectors.registry import CollectorRegistry
from device_watch_agent.config import AgentSettingsError, load_settings
from device_watch_agent.lifecycle import AgentRuntime
from device_watch_agent.logging import setup_logging
from device_watch_agent.transport.enrollment import EnrollmentClient, EnrollmentError

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


async def _run(*, enroll: bool = False) -> None:
    settings = load_settings()
    registry = CollectorRegistry()
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    _install_signal_handlers(stop_event, loop)
    if enroll:
        if stop_event.is_set():
            return
        enrollment = asyncio.create_task(EnrollmentClient(settings).ensure_enrolled())
        stopping = asyncio.create_task(stop_event.wait())
        try:
            done, _ = await asyncio.wait(
                {enrollment, stopping}, return_when=asyncio.FIRST_COMPLETED
            )
            if enrollment in done:
                enrollment.result()
                logger.info("agent enrollment ready")
        finally:
            for task in (enrollment, stopping):
                if not task.done():
                    task.cancel()
            await asyncio.gather(enrollment, stopping, return_exceptions=True)
        return
    await AgentRuntime(settings.interval_seconds, registry).run(stop_event)


def main(argv: list[str] | None = None) -> int:
    """Run the service, or explicitly enroll once and exit without printing identity."""

    parser = argparse.ArgumentParser(description="Device Watch agent")
    parser.add_argument(
        "--enroll",
        action="store_true",
        help="explicitly enroll if no identity is stored, then exit",
    )
    args = parser.parse_args(argv)
    setup_logging()
    try:
        asyncio.run(_run(enroll=args.enroll))
    except EnrollmentError as exc:
        logger.error("agent enrollment unavailable", extra={"state": exc.state.value})
        return 1
    except AgentSettingsError:
        logger.error("agent configuration unavailable")
        return 1
    except KeyboardInterrupt:
        return 0
    return 0


__all__ = ["main"]
