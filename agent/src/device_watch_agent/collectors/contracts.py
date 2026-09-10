"""Typed collector result contracts for future device monitoring."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Protocol, runtime_checkable

CollectorScalar = str | int | float | bool | None


class CollectorStatus(str, Enum):
    """Status variants for a collector execution."""

    SUCCESS = "success"
    UNAVAILABLE = "unavailable"
    FAILURE = "failure"


@dataclass(frozen=True, slots=True)
class CollectorResult:
    """Metadata summarizing a collector attempt without domain fields."""

    status: CollectorStatus
    values: Mapping[str, CollectorScalar] = field(
        default_factory=lambda: MappingProxyType({})
    )
    detail: str | None = None

    def __post_init__(self) -> None:
        """Ensure values are read-only and keyed by scalar values only."""

        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))


@runtime_checkable
class Collector(Protocol):
    """Runtime-checkable protocol expected of a collector implementation."""

    name: str

    async def collect(self) -> CollectorResult:
        """Collect a single result payload."""
        ...


__all__ = ["Collector", "CollectorResult", "CollectorScalar", "CollectorStatus"]
