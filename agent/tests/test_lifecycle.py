from __future__ import annotations

import asyncio

import pytest

from device_watch_agent.collectors.contracts import CollectorResult, CollectorStatus
from device_watch_agent.collectors.registry import CollectorRegistry
from device_watch_agent.lifecycle import AgentRuntime


class LocalCollector:
    name = "test-only"
    calls = 0

    async def collect(self) -> CollectorResult:
        self.calls += 1
        return CollectorResult(status=CollectorStatus.SUCCESS, values={"ok": True})


@pytest.mark.asyncio
async def test_runtime_waits_efficiently_and_stops_without_collecting() -> None:
    stop_event = asyncio.Event()
    collector = LocalCollector()
    registry = CollectorRegistry()
    registry.register(collector)
    runtime = AgentRuntime(30.0, registry)

    task = asyncio.create_task(runtime.run(stop_event))
    await asyncio.sleep(0)
    assert not task.done()
    assert collector.calls == 0
    stop_event.set()
    await asyncio.wait_for(task, timeout=1.0)


@pytest.mark.asyncio
async def test_runtime_cancellation_propagates_cleanly() -> None:
    task = asyncio.create_task(AgentRuntime(30.0, CollectorRegistry()).run(asyncio.Event()))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
