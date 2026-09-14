"""Step 10 on an empty, dedicated MySQL 8.x test database, run serially.

Requires DEVICE_WATCH_ENV=test, DEVICE_WATCH_DISPOSABLE_DATABASE=1 and protected
DATABASE_URL configuration. Accepts only an empty schema or an empty baseline/
Step 02 schema; refuses other revisions, tables, views or existing device rows.
Only fixture devices are inserted/deleted. Finishes at Step 02 after verifying
the 0005 -> 0004 -> 0005 -> 0002 -> 0005 -> 0002 round trip. Never use a database
shared with an application or another test suite.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import UUID

import pytest
from alembic.config import Config
from alembic.util.exc import CommandError
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from alembic import command
from device_watch_server.core.config import load_settings
from device_watch_server.db.connectivity import device_connectivity_table as state_table
from device_watch_server.db.engine import create_database_engine
from device_watch_server.domain.contracts import DeviceIdentity
from device_watch_server.enrollment.persistence import devices_table, insert_device

pytestmark = pytest.mark.integration
IDENTITY = "20260908_0002"
PREVIOUS = "20260913_0004"
REVISION = "20260914_0005"
IDENTITY_COLUMNS = {"device_id", "display_name", "created_at", "lifecycle"}
STATE_COLUMNS = {
    "last_seen_at",
    "last_heartbeat_submission_id",
    "last_agent_version",
}
TABLES = {"alembic_version", "devices", "enrollment_bootstraps", "device_credentials"}
DEVICE_IDS = (
    "12345678-1234-4234-8234-123456789abc",
    "22345678-1234-4234-8234-123456789abc",
)
SUBMISSION = "32345678-1234-4234-8234-123456789abc"
NEXT_SUBMISSION = "42345678-1234-4234-8234-123456789abc"
# MySQL DATETIME carries UTC by convention, without timezone metadata.
RECEIVED = datetime(2026, 9, 14, 12, 0, 0, 123456, tzinfo=UTC).replace(tzinfo=None)


def _require(condition: bool, message: str) -> None:
    if not condition:
        pytest.fail(message, pytrace=False)


@contextmanager
def _safe_database_errors() -> Iterator[None]:
    try:
        yield
    except (SQLAlchemyError, CommandError, ValueError, OSError):
        pytest.fail("Connectivity migration check failed; details withheld", pytrace=False)


def _migrate(revision: str, *, downgrade: bool = False) -> None:
    with _safe_database_errors():
        operation = command.downgrade if downgrade else command.upgrade
        operation(Config("server/alembic.ini"), revision)


@pytest.fixture
def mysql_engine() -> Iterator[Engine]:
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not configured for Step 10 MySQL migration tests")
    _require(
        os.environ.get("DEVICE_WATCH_ENV") == "test"
        and os.environ.get("DEVICE_WATCH_DISPOSABLE_DATABASE") == "1",
        "Require test mode and DEVICE_WATCH_DISPOSABLE_DATABASE=1",
    )
    with _safe_database_errors():
        engine = create_database_engine(load_settings())
    try:
        with _safe_database_errors(), engine.connect() as connection:
            version = str(connection.execute(text("SELECT VERSION()")).scalar_one())
            _require(version.startswith("8."), "Require MySQL 8.x")
            inspector = inspect(connection)
            tables = set(inspector.get_table_names())
            _require(not inspector.get_view_names(), "Refusing a schema with views")
            _require(
                tables <= {"alembic_version", "devices"},
                "Require an empty database or empty Step 02 schema",
            )
            if "alembic_version" in tables:
                revisions = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalars().all()
                _require(
                    revisions in ([], ["20260831_0001"], [IDENTITY]),
                    "Refusing an unexpected migration revision",
                )
                expected = {"alembic_version"}
                if revisions == [IDENTITY]:
                    expected.add("devices")
                _require(tables == expected, "Refusing an inconsistent schema")
            else:
                _require(not tables, "Refusing an unversioned nonempty schema")
            if "devices" in tables:
                _require(
                    connection.execute(text("SELECT 1 FROM devices LIMIT 1")).first()
                    is None,
                    "Refusing existing device rows",
                )
        _migrate(IDENTITY)
        yield engine
    finally:
        engine.dispose()


def test_mysql_connectivity_schema_constraints_and_round_trip(
    mysql_engine: Engine,
) -> None:
    engine = mysql_engine
    with _safe_database_errors():
        with engine.begin() as connection:
            for device_id in DEVICE_IDS:
                insert_device(
                    connection,
                    DeviceIdentity(
                        device_id=UUID(device_id),
                        display_name="Step 10 fixture",
                        created_at=datetime(2026, 9, 14, 11, tzinfo=UTC),
                    ),
                )
        identity_select = select(
            devices_table.c.device_id,
            devices_table.c.display_name,
            devices_table.c.created_at,
            devices_table.c.lifecycle,
        ).order_by(devices_table.c.device_id)
        with engine.connect() as connection:
            identities = connection.execute(identity_select).all()
        try:
            _migrate(REVISION)
            with engine.connect() as connection:
                inspector = inspect(connection)
                assert set(inspector.get_table_names()) == TABLES  # No history table.
                assert connection.execute(identity_select).all() == identities
                columns = {
                    column["name"]: column
                    for column in inspector.get_columns("devices")
                }
                assert set(columns) == IDENTITY_COLUMNS | STATE_COLUMNS
                assert all(columns[name]["nullable"] for name in STATE_COLUMNS)
                assert all(columns[name]["default"] is None for name in STATE_COLUMNS)
                assert getattr(columns["last_seen_at"]["type"], "fsp", None) == 6
                assert str(columns["last_heartbeat_submission_id"]["type"]) == "VARCHAR(36)"
                assert str(columns["last_agent_version"]["type"]) == "VARCHAR(64)"
                assert inspector.get_pk_constraint("devices")["constrained_columns"] == [
                    "device_id"
                ]
                assert inspector.get_foreign_keys("devices") == []
                assert inspector.get_unique_constraints("devices") == []
                assert any(
                    item["name"] == "ix_devices_last_seen_at"
                    and item["column_names"] == ["last_seen_at"]
                    and not item["unique"]
                    for item in inspector.get_indexes("devices")
                )
                assert any(
                    item["name"] == "ck_devices_submission_requires_last_seen"
                    for item in inspector.get_check_constraints("devices")
                )
                assert connection.execute(
                    select(
                        state_table.c.last_seen_at,
                        state_table.c.last_heartbeat_submission_id,
                        state_table.c.last_agent_version,
                    )
                ).tuples().all() == [(None, None, None), (None, None, None)]

            # The domain forbids a retained submission without a receipt timestamp.
            with pytest.raises(IntegrityError), engine.begin() as connection:
                connection.execute(
                    state_table.update().values(last_heartbeat_submission_id=SUBMISSION)
                )
            # Existing PK enforces one row per device; no new global UUID uniqueness.
            with pytest.raises(IntegrityError), engine.begin() as connection:
                connection.execute(
                    devices_table.insert().values(
                        device_id=DEVICE_IDS[0],
                        display_name="Duplicate fixture",
                        created_at=RECEIVED,
                        lifecycle="active",
                    )
                )
            with engine.begin() as connection:
                connection.execute(
                    state_table.update().values(
                        last_seen_at=RECEIVED,
                        last_heartbeat_submission_id=SUBMISSION,
                        last_agent_version="0.2.0",
                    )
                )
            with engine.connect() as connection:
                assert connection.execute(
                    select(state_table.c.last_seen_at)
                ).scalars().all() == [RECEIVED, RECEIVED]
            with engine.begin() as connection:
                connection.execute(
                    state_table.update().where(
                        state_table.c.device_id == DEVICE_IDS[0]
                    ).values(last_heartbeat_submission_id=NEXT_SUBMISSION)
                )
            with engine.connect() as connection:
                assert connection.execute(identity_select).all() == identities
                assert connection.execute(
                    select(state_table.c.last_heartbeat_submission_id).order_by(
                        state_table.c.device_id
                    )
                ).scalars().all() == [NEXT_SUBMISSION, SUBMISSION]
                assert set(inspect(connection).get_table_names()) == TABLES

            _migrate(PREVIOUS, downgrade=True)
            with engine.connect() as connection:
                inspector = inspect(connection)
                assert set(inspector.get_table_names()) == TABLES
                assert {col["name"] for col in inspector.get_columns("devices")} == (
                    IDENTITY_COLUMNS
                )
                assert not inspector.get_indexes("devices")
                assert not any(
                    item["name"] == "ck_devices_submission_requires_last_seen"
                    for item in inspector.get_check_constraints("devices")
                )
                assert connection.execute(identity_select).all() == identities
                assert connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one() == PREVIOUS
            _migrate(REVISION)
            with engine.connect() as connection:
                assert connection.execute(
                    select(state_table.c.last_seen_at)
                ).scalars().all() == [None, None]
            _migrate(IDENTITY, downgrade=True)
            with engine.connect() as connection:
                assert set(inspect(connection).get_table_names()) == {
                    "alembic_version", "devices"
                }
                assert connection.execute(identity_select).all() == identities
            _migrate(REVISION)
            with engine.connect() as connection:
                assert connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one() == REVISION
        finally:
            # Remove only these synthetic identities; never clear an entire table.
            with engine.begin() as connection:
                connection.execute(
                    devices_table.delete().where(
                        devices_table.c.device_id.in_(DEVICE_IDS)
                    )
                )
            _migrate(IDENTITY, downgrade=True)
