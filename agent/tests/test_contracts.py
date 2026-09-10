"""Tests for the collector result and protocol contracts."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import get_origin, get_type_hints

import pytest

from device_watch_agent.collectors.contracts import (
    Collector,
    CollectorResult,
    CollectorScalar,
    CollectorStatus,
)


class LocalCollector:
    name = "local"

    async def collect(self) -> CollectorResult:
        return CollectorResult(
            status=CollectorStatus.SUCCESS,
            values=MappingProxyType({"ok": True}),
            detail="tested",
        )


def test_success_result_and_runtime_protocol() -> None:
    result = CollectorResult(
        status=CollectorStatus.SUCCESS,
        values={"ok": True},
        detail="healthy",
    )
    assert result.status is CollectorStatus.SUCCESS
    assert result.values["ok"] is True
    assert result.detail == "healthy"
    assert isinstance(LocalCollector(), Collector)


def test_unavailable_and_failure_results_are_distinct() -> None:
    unavailable = CollectorResult(
        status=CollectorStatus.UNAVAILABLE,
        values={"probe": None},
        detail="not available",
    )
    failed = CollectorResult(
        status=CollectorStatus.FAILURE,
        values={"error": "probe failed"},
        detail="failed",
    )
    assert unavailable.status is CollectorStatus.UNAVAILABLE
    assert failed.status is CollectorStatus.FAILURE
    assert unavailable.values["probe"] is None
    assert failed.values["error"] == "probe failed"


def test_result_values_are_immutable() -> None:
    result = CollectorResult(status=CollectorStatus.SUCCESS, values={"count": 2})
    with pytest.raises(TypeError):
        result.values["count"] = 9


def test_result_values_expose_the_mapping_contract_and_copy_input() -> None:
    source: Mapping[str, CollectorScalar] = {"count": 2}

    result = CollectorResult(status=CollectorStatus.SUCCESS, values=source)

    assert get_origin(get_type_hints(CollectorResult)["values"]) is Mapping
    assert result.values == {"count": 2}

    mutable_source = {"count": 2}
    copied_result = CollectorResult(
        status=CollectorStatus.SUCCESS,
        values=mutable_source,
    )
    mutable_source["count"] = 9
    assert copied_result.values == {"count": 2}
