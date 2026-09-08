"""Database connectivity checks for readiness validation."""

from __future__ import annotations

import logging

from sqlalchemy import Engine, text

logger = logging.getLogger("device_watch_server.db")


def check_database(engine: Engine) -> None:
    """Execute a lightweight SQL probe to confirm the database is reachable."""

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("database unavailable", extra={"event": "database_unavailable"})
        raise RuntimeError("database unavailable") from exc


__all__ = ["check_database"]
