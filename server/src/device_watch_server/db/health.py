"""Database connectivity checks for readiness validation."""

from __future__ import annotations

from sqlalchemy import Engine, text


def check_database(engine: Engine) -> None:
    """Execute a lightweight SQL probe to confirm the database is reachable."""

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


__all__ = ["check_database"]
