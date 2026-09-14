"""Strict environment configuration for the native agent."""

from __future__ import annotations

import base64
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path
from urllib.parse import urlsplit

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
    server_url: str | None = field(default=None, repr=False)
    bootstrap_secret: str | None = field(default=None, repr=False)
    display_name: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.server_url is not None:
            try:
                url = urlsplit(self.server_url)
                if (
                    url.scheme != "https"
                    or not url.hostname
                    or url.username is not None
                    or url.password is not None
                    or url.path not in ("", "/")
                    or "?" in self.server_url
                    or "#" in self.server_url
                    or "\\" in self.server_url
                    or any(char.isspace() or ord(char) < 32 for char in self.server_url)
                    or (url.port is not None and not 1 <= url.port <= 65535)
                ):
                    raise ValueError
            except (ValueError, TypeError):
                raise AgentSettingsError(
                    "DEVICE_WATCH_AGENT_SERVER_URL must be an HTTPS origin without user info, path, query or fragment"
                ) from None
            object.__setattr__(self, "server_url", self.server_url.rstrip("/"))
        if self.bootstrap_secret is not None:
            try:
                if not re.fullmatch(r"dwb_v1_[A-Za-z0-9_-]{43}", self.bootstrap_secret):
                    raise ValueError
                encoded = self.bootstrap_secret[7:]
                raw = base64.b64decode(encoded + "=", altchars=b"-_", validate=True)
                if (
                    len(raw) != 32
                    or base64.urlsafe_b64encode(raw).decode().rstrip("=") != encoded
                ):
                    raise ValueError
            except (ValueError, TypeError):
                raise AgentSettingsError("Invalid enrollment bootstrap input") from None
        if self.display_name is not None:
            if not 1 <= len(self.display_name) <= 120 or not self.display_name.strip():
                raise AgentSettingsError(
                    "Enrollment display name must contain 1 to 120 characters"
                )
            object.__setattr__(self, "display_name", self.display_name.strip())


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
            "DEVICE_WATCH_AGENT_SERVER_URL",
            "DEVICE_WATCH_AGENT_BOOTSTRAP_SECRET",
            "DEVICE_WATCH_AGENT_DISPLAY_NAME",
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

    return AgentSettings(
        mode=mode,
        interval_seconds=interval,
        identity_path=path,
        server_url=values.get("DEVICE_WATCH_AGENT_SERVER_URL"),
        bootstrap_secret=values.get("DEVICE_WATCH_AGENT_BOOTSTRAP_SECRET"),
        display_name=values.get("DEVICE_WATCH_AGENT_DISPLAY_NAME"),
    )


__all__ = ["AgentSettings", "AgentSettingsError", "load_settings"]
