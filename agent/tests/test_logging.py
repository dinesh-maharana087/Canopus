"""Tests for newline-delimited structured agent logging."""

from __future__ import annotations

import io
import json
import logging

from device_watch_agent.logging import AgentFormatter


def test_formatter_emits_one_json_object_per_record_with_structured_extras() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(AgentFormatter())
    # Keep this formatter test isolated from global logging state.
    logger = logging.Logger("agent-structured-logging-test")  # noqa: LOG001
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info(
        "agent started with %d collectors",
        0,
        extra={"event": "agent_started"},
    )
    logger.warning("signal received", extra={"signal": "SIGTERM"})

    lines = stream.getvalue().splitlines()
    assert len(lines) == 2

    started = json.loads(lines[0])
    assert started["level"] == "info"
    assert started["message"] == "agent started with 0 collectors"
    assert started["event"] == "agent_started"
    assert isinstance(started["timestamp"], str)

    signalled = json.loads(lines[1])
    assert signalled["level"] == "warning"
    assert signalled["message"] == "signal received"
    assert signalled["signal"] == "SIGTERM"
    assert isinstance(signalled["timestamp"], str)
