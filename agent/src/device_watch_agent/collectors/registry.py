"""Unique-name registry for collector implementations."""

from __future__ import annotations

from collections.abc import Sequence

from device_watch_agent.collectors.contracts import Collector


class CollectorRegistry:
    """Registry for collector implementations with a stable insertion order."""

    def __init__(self) -> None:
        self._collectors: list[Collector] = []

    def register(self, collector: Collector) -> None:
        """Register a collector under a unique, non-blank name."""

        name = collector.name.strip()
        if not name:
            raise ValueError("Collector name must be non-empty")
        if any(existing.name == name for existing in self._collectors):
            raise ValueError(f"Duplicate collector name: {name}")
        self._collectors.append(collector)

    def snapshot(self) -> tuple[Collector, ...]:
        """Return an immutable snapshot of the registered collectors."""

        return tuple(self._collectors)

    def __bool__(self) -> bool:
        return bool(self._collectors)

    def __len__(self) -> int:
        return len(self._collectors)

    @property
    def collectors(self) -> Sequence[Collector]:
        """Return the underlying sequence without mutating it."""

        return tuple(self._collectors)


__all__ = ["CollectorRegistry"]
