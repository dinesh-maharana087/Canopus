"""Real-MySQL verification for the Stage 2 device identity migration."""

from __future__ import annotations

import os

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from device_watch_server.core.config import Settings

pytestmark = pytest.mark.integration


def _database_url() -> str:
    value = os.environ.get("DATABASE_URL")
    if not value:
        pytest.skip("DATABASE_URL is not configured for integration testing")
    return value


def test_device_identity_migration_is_reversible_and_constrained() -> None:
    url = _database_url()
    settings = Settings(device_watch_env="test", database_url=url)
    engine = create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)
    alembic_cfg = Config("server/alembic.ini")

    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "20260908_0002")

    with engine.begin() as connection:
        current = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert current == "20260908_0002"

        inspector = inspect(connection)
        assert inspector.get_table_names() == ["alembic_version", "devices"]
        columns = {column["name"]: column for column in inspector.get_columns("devices")}
        assert set(columns) == {"device_id", "display_name", "created_at", "lifecycle"}
        assert columns["device_id"]["nullable"] is False
        assert columns["display_name"]["nullable"] is False
        assert columns["created_at"]["nullable"] is False
        assert columns["lifecycle"]["nullable"] is False
        assert str(columns["device_id"]["type"]).upper().startswith("VARCHAR(36)")
        assert str(columns["display_name"]["type"]).upper().startswith("VARCHAR(120)")

        constraints = inspector.get_check_constraints("devices")
        assert any(constraint["name"] == "ck_devices_lifecycle" for constraint in constraints)
        primary_key = inspector.get_pk_constraint("devices")
        assert primary_key["constrained_columns"] == ["device_id"]

        connection.execute(
            text(
                "INSERT INTO devices (device_id, display_name, created_at, lifecycle) "
                "VALUES (:device_id, :display_name, :created_at, :lifecycle)"
            ),
            {
                "device_id": "123e4567-e89b-42d3-a456-426614174000",
                "display_name": "workstation",
                "created_at": "2026-09-08 12:00:00",
                "lifecycle": "active",
            },
        )

        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO devices (device_id, display_name, created_at, lifecycle) "
                    "VALUES (:device_id, :display_name, :created_at, :lifecycle)"
                ),
                {
                    "device_id": "123e4567-e89b-42d3-a456-426614174000",
                    "display_name": "another name",
                    "created_at": "2026-09-08 12:00:01",
                    "lifecycle": "active",
                },
            )

    command.downgrade(alembic_cfg, "20260831_0001")
    with engine.connect() as connection:
        assert inspect(connection).get_table_names() == ["alembic_version"]

    command.upgrade(alembic_cfg, "20260908_0002")
