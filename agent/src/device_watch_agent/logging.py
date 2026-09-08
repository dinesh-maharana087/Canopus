"""Small standard-library logging setup for the native agent."""

from __future__ import annotations

import logging


class AgentFormatter(logging.Formatter):
    """Keep agent logs compact and operationally useful."""

    def format(self, record: logging.LogRecord) -> str:
        return f"{record.levelname.lower()} {record.getMessage()}"


def setup_logging() -> None:
    """Configure one stderr handler when the application starts."""

    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(AgentFormatter())
        root.addHandler(handler)
    root.setLevel(logging.INFO)


__all__ = ["setup_logging"]
