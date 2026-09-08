"""Centralized SQLAlchemy engine construction for the Device Watch server."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine, make_url

from device_watch_server.core.config import (
    PRODUCTION_TLS_QUERY,
    Environment,
    Settings,
)


def validated_connect_args(settings: Settings) -> dict[str, object]:
    """Return the exact flat PyMySQL TLS arguments for production only."""

    if settings.device_watch_env is not Environment.PRODUCTION:
        return {}

    return {
        "ssl_ca": PRODUCTION_TLS_QUERY["ssl_ca"],
        "ssl_verify_cert": True,
        "ssl_verify_identity": True,
    }


def database_engine_url(settings: Settings) -> URL:
    """Return the canonical engine URL without production TLS query keys."""

    url = make_url(settings.database_url.get_secret_value())
    if settings.device_watch_env is not Environment.PRODUCTION:
        return url

    query = dict(url.query)
    for key in PRODUCTION_TLS_QUERY:
        query.pop(key, None)
    return url.set(query=query)


def create_database_engine(settings: Settings) -> Engine:
    """Create and configure the server's SQLAlchemy engine."""

    return create_engine(
        database_engine_url(settings),
        pool_pre_ping=True,
        pool_recycle=1_800,
        connect_args=validated_connect_args(settings),
    )


__all__ = [
    "create_database_engine",
    "database_engine_url",
    "validated_connect_args",
]
