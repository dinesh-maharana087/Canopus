"""Strict environment configuration for the native agent."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path

from device_watch_agent.identity import (
    IdentityError,
    default_identity_path,
    validate_identity_path,
)


class AgentSettingsError(ValueError):
    """Raised when the agent environment is missing or unsafe."""


@dataclass(frozen=True, slots=True)
class AgentSettings:
    """Validated runtime and protected identity-file configuration."""

    mode: str
    interval_seconds: float = 30.0
    identity_path: Path = field(default_factory=default_identity_path)


def load_settings(environ: Mapping[str, str] | None = None) -> AgentSettings:
    """Load only the dedicated agent variables from the environment."""

    values = os.environ if environ is None else environ
    unknown = sorted(
        key
        for key in values
        if key.startswith("DEVICE_WATCH_AGENT_")
        and key
        not in {
            "DEVICE_WATCH_AGENT_MODE",
            "DEVICE_WATCH_AGENT_INTERVAL_SECONDS",
            "DEVICE_WATCH_AGENT_IDENTITY_PATH",
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
    if not isfinite(interval) or interval <= 0:
        raise AgentSettingsError(
            "DEVICE_WATCH_AGENT_INTERVAL_SECONDS must be a positive number"
        )

    try:
        raw_path = values.get("DEVICE_WATCH_AGENT_IDENTITY_PATH")
        path = (
            default_identity_path(values)
            if raw_path is None
            else validate_identity_path(Path(raw_path))
        )
    except (IdentityError, ValueError, TypeError):
        raise AgentSettingsError(
            "DEVICE_WATCH_AGENT_IDENTITY_PATH must be a safe absolute path"
        ) from None

    return AgentSettings(mode=mode, interval_seconds=interval, identity_path=path)


__all__ = ["AgentSettings", "AgentSettingsError", "load_settings"]
