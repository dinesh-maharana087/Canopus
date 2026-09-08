"""Tests for collector registry behavior."""

from __future__ import annotations

import pytest

from device_watch_agent.collectors.contracts import CollectorResult, CollectorStatus
from device_watch_agent.collectors.registry import CollectorRegistry


class LocalCollector:
    def __init__(self, name: str) -> None:
        self.name = name

    async def collect(self) -> CollectorResult:
        return CollectorResult(status=CollectorStatus.SUCCESS, values={"ok": True})


def test_empty_registry_is_valid() -> None:
    registry = CollectorRegistry()
    assert bool(registry) is False
    assert len(registry) == 0
    assert registry.snapshot() == ()
    assert registry.collectors == ()


def test_registry_preserves_registration_order_and_rejects_duplicates() -> None:
    registry = CollectorRegistry()
    first = LocalCollector("alpha")
    second = LocalCollector("beta")

    registry.register(first)
    registry.register(second)

    snapshot = registry.snapshot()
    assert snapshot == (first, second)
    assert tuple(item.name for item in snapshot) == ("alpha", "beta")

    with pytest.raises(ValueError, match="Duplicate collector name"):
        registry.register(LocalCollector("alpha"))


def test_registry_rejects_blank_names() -> None:
    registry = CollectorRegistry()

    class BlankCollector:
        name = "   "

        async def collect(self) -> CollectorResult:
            return CollectorResult(status=CollectorStatus.SUCCESS, values={"ok": True})

    with pytest.raises(ValueError, match="non-empty"):
        registry.register(BlankCollector())
