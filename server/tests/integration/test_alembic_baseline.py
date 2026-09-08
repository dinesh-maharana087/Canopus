"""Alembic baseline verification against a real MySQL instance."""

from __future__ import annotations

import os

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from device_watch_server.core.config import Settings
from device_watch_server.db.base import Base

pytestmark = pytest.mark.integration


def _database_url() -> str:
    value = os.environ.get("DATABASE_URL")
    if not value:
        pytest.skip("DATABASE_URL is not configured for integration testing")
    return value


def test_real_mysql_baseline_cycle() -> None:
    url = _database_url()
    settings = Settings(device_watch_env="test", database_url=url)
    engine = create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)

    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))

    alembic_cfg = Config("server/alembic.ini")
    command.upgrade(alembic_cfg, "20260831_0001")

    with engine.connect() as connection:
        current = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert current == "20260831_0001"
        assert Base.metadata.tables == {}
        inspector = inspect(connection)
        assert inspector.get_table_names() == []

    command.downgrade(alembic_cfg, "base")
    with engine.connect() as connection:
        tables = inspect(connection).get_table_names()
        assert tables == []
        assert connection.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'alembic_version'")) .scalar() == 0

    command.upgrade(alembic_cfg, "20260831_0001")
    with engine.connect() as connection:
        current = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert current == "20260831_0001"
        assert Base.metadata.tables == {}
