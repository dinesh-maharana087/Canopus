"""Collector contracts and registry for the Device Watch agent."""

from device_watch_agent.collectors.contracts import (
    Collector,
    CollectorResult,
    CollectorStatus,
)
from device_watch_agent.collectors.registry import CollectorRegistry

__all__ = [
    "Collector",
    "CollectorRegistry",
    "CollectorResult",
    "CollectorStatus",
]
