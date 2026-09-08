"""Strict environment configuration for the native agent."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


class AgentSettingsError(ValueError):
    """Raised when the agent environment is missing or unsafe."""


@dataclass(frozen=True, slots=True)
class AgentSettings:
    """Validated configuration for the Stage 1 agent runtime."""

    mode: str
    interval_seconds: float = 30.0


def load_settings(environ: Mapping[str, str] | None = None) -> AgentSettings:
    """Load only the dedicated agent variables from the environment."""

    values = os.environ if environ is None else environ
    unknown = sorted(
        key
        for key in values
        if key.startswith("DEVICE_WATCH_AGENT_")
        and key not in {
            "DEVICE_WATCH_AGENT_MODE",
            "DEVICE_WATCH_AGENT_INTERVAL_SECONDS",
        }
    )
    if unknown:
        raise AgentSettingsError(f"Unknown agent setting: {unknown[0]}")

    mode = values.get("DEVICE_WATCH_AGENT_MODE")
    if mode is None:
        raise AgentSettingsError("DEVICE_WATCH_AGENT_MODE is required")
    if mode != "service":
        raise AgentSettingsError("DEVICE_WATCH_AGENT_MODE must be 'service'")

    raw_interval = values.get("DEVICE_WATCH_AGENT_INTERVAL_SECONDS", "30.0")
    try:
        interval = float(raw_interval)
    except ValueError as exc:
        raise AgentSettingsError(
            "DEVICE_WATCH_AGENT_INTERVAL_SECONDS must be a positive number"
        ) from exc
    if interval <= 0:
        raise AgentSettingsError(
            "DEVICE_WATCH_AGENT_INTERVAL_SECONDS must be a positive number"
        )

    return AgentSettings(mode=mode, interval_seconds=interval)


__all__ = ["AgentSettings", "AgentSettingsError", "load_settings"]
