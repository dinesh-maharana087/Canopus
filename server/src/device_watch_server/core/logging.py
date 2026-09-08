"""Secret-safe structured logging helpers for the Device Watch server."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlsplit

_SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "cookie",
    "cookies",
    "password",
    "passwd",
    "secret",
    "token",
    "url",
    "uri",
    "database_url",
    "access_token",
    "refresh_token",
    "client_secret",
    "ssl_ca",

}


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in _SENSITIVE_KEYS or any(part in lowered for part in ("token", "secret", "password", "cookie", "authorization", "api_key", "pass", "credential"))


def _redact_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "[REDACTED]"
    if not parsed.scheme:
        return value

    if parsed.username is not None or parsed.password is not None:
        host = parsed.hostname or ""
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
        netloc = f"REDACTED@{host}" if host else "REDACTED"
    else:
        netloc = parsed.netloc

    query = ""
    if parsed.query:
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
        redacted_pairs: list[str] = []
        for key, item in pairs:
            if _is_sensitive_key(key):
                redacted_pairs.append(f"{key}=[REDACTED]")
            else:
                redacted_pairs.append(f"{key}={item}")
        query = "&".join(redacted_pairs)

    return f"{parsed.scheme}://{netloc}{parsed.path}?{query}" if query else f"{parsed.scheme}://{netloc}{parsed.path}"


def sanitize_for_logging(value: Any, parent_key: str | None = None) -> Any:
    """Return a copy of value with secrets removed from nested payloads."""
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_name = str(key)
            if _is_sensitive_key(key_name):
                if key_name.lower() in {"url", "uri", "database_url"} and isinstance(item, str):
                    result[key_name] = _redact_url(item)
                else:
                    result[key_name] = "[REDACTED]"
            else:
                result[key_name] = sanitize_for_logging(item, key_name)
        return result

    if isinstance(value, list):
        return [sanitize_for_logging(item, parent_key) for item in value]

    if isinstance(value, tuple):
        return tuple(sanitize_for_logging(item, parent_key) for item in value)

    if isinstance(value, str):
        if parent_key and _is_sensitive_key(parent_key):
            if parent_key.lower() in {"url", "uri", "database_url"} and "://" in value:
                return _redact_url(value)
            return "[REDACTED]"
        if "://" in value:
            return _redact_url(value)
        return value

    return value


class JSONFormatter(logging.Formatter):
    """Emit a JSON log record with the approved operational fields only."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extras = {
            "event",
            "method",
            "path",
            "normalized_path",
            "status",
            "duration_ms",
        }
        for name in extras:
            value = getattr(record, name, None)
            if value is not None:
                payload[name] = value
        payload = sanitize_for_logging(payload)
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def setup_logging() -> logging.Logger:
    """Configure a single JSON stdout logger for the server."""

    logger = logging.getLogger("device_watch_server")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(isinstance(handler, logging.StreamHandler) and handler.stream is sys.stdout for handler in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        handler.terminator = ""
        logger.addHandler(handler)
    return logger


__all__ = ["JSONFormatter", "sanitize_for_logging", "setup_logging"]
