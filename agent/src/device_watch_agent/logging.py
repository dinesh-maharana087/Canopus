"""Small standard-library logging setup for the native agent."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

_STANDARD_RECORD_FIELDS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"asctime", "message"}


class AgentFormatter(logging.Formatter):
    """Render compact newline-delimited JSON records."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_RECORD_FIELDS
        }
        payload.update(
            {
                "level": record.levelname.lower(),
                "message": record.getMessage(),
                "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            }
        )
        return json.dumps(
            payload,
            default=str,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )


def setup_logging() -> None:
    """Configure one stderr handler when the application starts."""

    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(AgentFormatter())
        root.addHandler(handler)
    root.setLevel(logging.INFO)


__all__ = ["setup_logging"]
