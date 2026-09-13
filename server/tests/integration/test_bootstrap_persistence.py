"""Step 03 checks against a dedicated, disposable MySQL 8.x database.

Operators must set DEVICE_WATCH_ENV=test and supply DATABASE_URL through protected
configuration for a database used only by this module. Run this module serially;
do not share its database with an application, another test suite, or pytest-xdist.
The fixture recreates enrollment_bootstraps through explicit 0002/0003 migrations
and leaves revision 0003 installed. Existing device rows are never deleted. Unknown
tables, views, and migration revisions cause a failure before any migration runs.
Absent DATABASE_URL skips the module's shared database fixture without connecting.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Barrier, BrokenBarrierError
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.util.exc import CommandError
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from alembic import command
from device_watch_server.core.config import Environment, load_settings
from device_watch_server.db.engine import create_database_engine
from device_watch_server.enrollment.bootstrap import (
    DIGEST_VERSION,
    bootstrap_fingerprint,
    verify_bootstrap_digest,
)
from device_watch_server.enrollment.repository import (
    bootstrap_table,
    insert_bootstrap,
    lookup_bootstrap_by_fingerprint,
    lookup_bootstrap_by_id,
)
from device_watch_server.enrollment.service import (
    GENERIC_BOOTSTRAP_FAILURE,
    BootstrapServiceError,
    provision_bootstrap,
    revoke_bootstrap,
    validate_and_consume_bootstrap,
)

pytestmark = pytest.mark.integration

IDENTITY_REVISION = "20260908_0002"
BOOTSTRAP_REVISION = "20260908_0003"
NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
TEST_PEPPER = "bootstrap-integration-fixture-pepper-32-bytes-minimum"
_REVISION_TABLES = {
    None: set(),
    "20260831_0001": {"alembic_version"},
    IDENTITY_REVISION: {"alembic_version", "devices"},
    BOOTSTRAP_REVISION: {"alembic_version", "devices", "enrollment_bootstraps"},
}


def _require(condition: bool, message: str) -> None:
    """Report fixed diagnostics without expanding secret-bearing objects."""
    if not condition:
        pytest.fail(message, pytrace=False)


@contextmanager
def _safe_database_errors() -> Iterator[None]:
    try:
        yield
    except SQLAlchemyError:
        pytest.fail(
            "MySQL bootstrap operation failed; database details withheld", pytrace=False
        )


def _known_revision(connection: Connection) -> str | None:
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    _require(not inspector.get_view_names(), "Refusing a database containing views")
    _require(
        tables <= _REVISION_TABLES[BOOTSTRAP_REVISION],
        "Refusing a database containing tables outside the Step 03 allowlist",
    )
    if "alembic_version" not in tables:
        _require(not tables, "Refusing an unversioned, nonempty database")
        return None
    revisions = (
        connection.execute(text("SELECT version_num FROM alembic_version"))
        .scalars()
        .all()
    )
    if not revisions:
        _require(tables == {"alembic_version"}, "Refusing an inconsistent base schema")
        return None
    _require(len(revisions) == 1, "Refusing a database with multiple migration heads")
    revision = revisions[0]
    _require(revision in _REVISION_TABLES, "Refusing an unknown migration revision")
    _require(
        tables == _REVISION_TABLES[revision], "Refusing an inconsistent Step 03 schema"
    )
    return str(revision)


def _migrate(engine: Engine, *, downgrade: bool, revision: str) -> None:
    with _safe_database_errors(), engine.connect() as connection:
        _known_revision(connection)
    config = Config("server/alembic.ini")
    try:
        if downgrade:
            command.downgrade(config, revision)
        else:
            command.upgrade(config, revision)
    except (CommandError, SQLAlchemyError, ValueError, OSError):
        pytest.fail(
            "Bootstrap migration failed; database details withheld", pytrace=False
        )


@pytest.fixture(scope="module")
def mysql_engine() -> Iterator[Engine]:
    if not os.environ.get("DATABASE_URL"):
        pytest.skip(
            "DATABASE_URL is not configured for bootstrap MySQL integration tests"
        )
    _require(
        os.environ.get("DEVICE_WATCH_ENV") == "test",
        "Bootstrap migration tests require DEVICE_WATCH_ENV=test and a disposable database",
    )
    try:
        settings = load_settings()
        _require(
            settings.device_watch_env is Environment.TEST,
            "Refusing a non-test environment",
        )
        engine = create_database_engine(settings)
    except (SQLAlchemyError, ValueError, OSError):
        pytest.fail(
            "Bootstrap test database configuration failed; details withheld",
            pytrace=False,
        )
    try:
        with _safe_database_errors(), engine.connect() as connection:
            version = str(connection.execute(text("SELECT VERSION()")).scalar_one())
            _require(
                version.startswith("8."),
                "Bootstrap integration tests require MySQL 8.x",
            )
            _known_revision(connection)
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def bootstrap_database(mysql_engine: Engine) -> Engine:
    with _safe_database_errors(), mysql_engine.connect() as connection:
        revision = _known_revision(connection)
    if revision == BOOTSTRAP_REVISION:
        _migrate(mysql_engine, downgrade=True, revision=IDENTITY_REVISION)
    elif revision != IDENTITY_REVISION:
        _migrate(mysql_engine, downgrade=False, revision=IDENTITY_REVISION)
    _migrate(mysql_engine, downgrade=False, revision=BOOTSTRAP_REVISION)
    return mysql_engine


def test_bootstrap_migration_round_trip_preserves_the_device_schema(
    bootstrap_database: Engine,
) -> None:
    engine = bootstrap_database
    with _safe_database_errors(), engine.connect() as connection:
        _require(
            _known_revision(connection) == BOOTSTRAP_REVISION,
            "Bootstrap revision was not installed",
        )
        inspector = inspect(connection)
        device_columns = inspector.get_columns("devices")
        device_count = connection.execute(
            text("SELECT COUNT(*) FROM devices")
        ).scalar_one()
        columns = {
            column["name"]: column
            for column in inspector.get_columns("enrollment_bootstraps")
        }
        _require(
            set(columns)
            == {
                "bootstrap_id",
                "lookup_fingerprint",
                "digest_version",
                "digest",
                "operator_label",
                "created_at",
                "expires_at",
                "consumed_at",
                "revoked_at",
            },
            "Bootstrap schema has missing or unexpected columns",
        )
        required = {
            "bootstrap_id",
            "lookup_fingerprint",
            "digest_version",
            "digest",
            "created_at",
            "expires_at",
        }
        _require(
            all(not columns[name]["nullable"] for name in required),
            "Required bootstrap columns are nullable",
        )
        _require(
            all(
                columns[name]["nullable"]
                for name in ("operator_label", "consumed_at", "revoked_at")
            ),
            "Optional bootstrap columns are not nullable",
        )
        _require(
            str(columns["lookup_fingerprint"]["type"]).upper() == "BINARY(32)",
            "Fingerprint storage has the wrong type",
        )
        _require(
            str(columns["digest"]["type"]).upper() == "BINARY(32)",
            "Digest storage has the wrong type",
        )
        primary_key = inspector.get_pk_constraint("enrollment_bootstraps")
        _require(
            primary_key["constrained_columns"] == ["bootstrap_id"],
            "Bootstrap primary key is missing",
        )
        unique = inspector.get_unique_constraints("enrollment_bootstraps")
        _require(
            any(item["column_names"] == ["lookup_fingerprint"] for item in unique),
            "Fingerprint uniqueness is missing",
        )
        checks = {
            item["name"]
            for item in inspector.get_check_constraints("enrollment_bootstraps")
        }
        _require(
            checks
            == {
                "ck_enrollment_bootstraps_expires_after_created",
                "ck_enrollment_bootstraps_terminal_exclusive",
                "ck_enrollment_bootstraps_consumed_not_before_created",
                "ck_enrollment_bootstraps_revoked_not_before_created",
            },
            "Bootstrap lifecycle database constraints are incomplete",
        )
    _migrate(engine, downgrade=True, revision=IDENTITY_REVISION)
    with _safe_database_errors(), engine.connect() as connection:
        _require(
            _known_revision(connection) == IDENTITY_REVISION,
            "Bootstrap downgrade did not restore Step 02",
        )
        inspector = inspect(connection)
        _require(
            str(inspector.get_columns("devices")) == str(device_columns),
            "Bootstrap migration changed device columns",
        )
        _require(
            connection.execute(text("SELECT COUNT(*) FROM devices")).scalar_one()
            == device_count,
            "Bootstrap migration changed device rows",
        )
    _migrate(engine, downgrade=False, revision=BOOTSTRAP_REVISION)
    with _safe_database_errors(), engine.connect() as connection:
        _require(
            _known_revision(connection) == BOOTSTRAP_REVISION,
            "Bootstrap re-upgrade failed",
        )


def test_bootstrap_digest_and_second_precision_timestamps_survive_commit(
    bootstrap_database: Engine,
) -> None:
    engine = bootstrap_database
    with _safe_database_errors():
        with engine.begin() as connection:
            created = provision_bootstrap(
                connection,
                TEST_PEPPER,
                operator_label=" integration fixture ",
                clock=lambda: NOW.replace(microsecond=987654),
            )
        engine.dispose()
        with engine.connect() as connection:
            stored = lookup_bootstrap_by_id(connection, created.bootstrap_id)
            _require(stored is not None, "Committed bootstrap was not durable")
            assert stored is not None
            fingerprint_match = lookup_bootstrap_by_fingerprint(
                connection, bootstrap_fingerprint(created.bootstrap_value)
            )
            _require(fingerprint_match is not None, "Digest fingerprint lookup failed")
            assert fingerprint_match is not None
            _require(
                fingerprint_match.bootstrap_id == created.bootstrap_id,
                "Fingerprint selected a different record",
            )
            _require(
                stored.digest_version == DIGEST_VERSION, "Stored digest version changed"
            )
            _require(
                verify_bootstrap_digest(
                    created.bootstrap_value, stored.digest, TEST_PEPPER
                ),
                "Stored bootstrap digest did not verify",
            )
            _require(
                stored.created_at == created.created_at == NOW,
                "Stored creation time differs from the provisioning result",
            )
            _require(
                stored.expires_at == created.expires_at == NOW + timedelta(minutes=15),
                "Stored expiry differs from the provisioning result",
            )
            _require(
                stored.operator_label == "integration fixture",
                "Operator label did not persist",
            )
            _require(
                stored.consumed_at is None and stored.revoked_at is None,
                "New bootstrap has a terminal timestamp",
            )


def test_mysql_rejects_duplicate_bootstrap_fingerprints(
    bootstrap_database: Engine,
) -> None:
    engine = bootstrap_database
    with _safe_database_errors():
        with engine.begin() as connection:
            created = provision_bootstrap(connection, TEST_PEPPER, clock=lambda: NOW)
        with engine.connect() as connection:
            stored = lookup_bootstrap_by_id(connection, created.bootstrap_id)
        _require(stored is not None, "Unique fingerprint fixture was not persisted")
        assert stored is not None
        with pytest.raises(IntegrityError), engine.begin() as connection:
            insert_bootstrap(connection, replace(stored, bootstrap_id=uuid4()))
        with engine.connect() as connection:
            count = len(
                connection.execute(select(bootstrap_table.c.bootstrap_id)).all()
            )
            _require(
                count == 1,
                "Duplicate fingerprint insertion changed the stored row count",
            )


@pytest.mark.parametrize("state", ("expired", "revoked", "consumed"))
def test_bootstrap_terminal_states_fail_generically_and_do_not_change(
    bootstrap_database: Engine,
    state: str,
) -> None:
    engine = bootstrap_database
    with _safe_database_errors():
        with engine.begin() as connection:
            created = provision_bootstrap(
                connection, TEST_PEPPER, expires_in_minutes=1, clock=lambda: NOW
            )
        terminal_at = NOW + timedelta(seconds=1)
        if state == "revoked":
            with engine.begin() as connection:
                revoke_bootstrap(
                    connection, created.bootstrap_id, clock=lambda: terminal_at
                )
        elif state == "consumed":
            with engine.begin() as connection:
                consumed_id = validate_and_consume_bootstrap(
                    connection,
                    created.bootstrap_value.to_wire(),
                    TEST_PEPPER,
                    clock=lambda: terminal_at,
                )
                _require(
                    consumed_id == created.bootstrap_id,
                    "Consumption returned a different bootstrap ID",
                )
        attempted_at = (
            created.expires_at if state == "expired" else NOW + timedelta(seconds=2)
        )
        with (
            pytest.raises(BootstrapServiceError) as failure,
            engine.begin() as connection,
        ):
            validate_and_consume_bootstrap(
                connection,
                created.bootstrap_value.to_wire(),
                TEST_PEPPER,
                clock=lambda: attempted_at,
            )
        _require(
            str(failure.value) == GENERIC_BOOTSTRAP_FAILURE,
            "Terminal-state error was not generic",
        )
        with (
            pytest.raises(BootstrapServiceError) as revoke_failure,
            engine.begin() as connection,
        ):
            revoke_bootstrap(
                connection, created.bootstrap_id, clock=lambda: attempted_at
            )
        _require(
            str(revoke_failure.value) == GENERIC_BOOTSTRAP_FAILURE,
            "Terminal revocation error was not generic",
        )
        with engine.connect() as connection:
            stored = lookup_bootstrap_by_id(connection, created.bootstrap_id)
        _require(stored is not None, "Terminal bootstrap record was lost")
        assert stored is not None
        _require(
            stored.consumed_at == (terminal_at if state == "consumed" else None),
            "Consumption state changed after rejection",
        )
        _require(
            stored.revoked_at == (terminal_at if state == "revoked" else None),
            "Revocation state changed after rejection",
        )


def test_bootstrap_insert_and_lifecycle_changes_follow_caller_rollback(
    bootstrap_database: Engine,
) -> None:
    engine = bootstrap_database
    with _safe_database_errors():
        with engine.connect() as connection:
            transaction = connection.begin()
            discarded = provision_bootstrap(connection, TEST_PEPPER, clock=lambda: NOW)
            transaction.rollback()
        with engine.connect() as connection:
            _require(
                lookup_bootstrap_by_id(connection, discarded.bootstrap_id) is None,
                "Provisioning escaped caller rollback",
            )
        with engine.begin() as connection:
            created = provision_bootstrap(connection, TEST_PEPPER, clock=lambda: NOW)
        with engine.connect() as connection:
            transaction = connection.begin()
            validate_and_consume_bootstrap(
                connection,
                created.bootstrap_value.to_wire(),
                TEST_PEPPER,
                clock=lambda: NOW + timedelta(seconds=1),
            )
            transaction.rollback()
        with engine.connect() as connection:
            transaction = connection.begin()
            revoke_bootstrap(
                connection,
                created.bootstrap_id,
                clock=lambda: NOW + timedelta(seconds=2),
            )
            transaction.rollback()
        with engine.connect() as connection:
            stored = lookup_bootstrap_by_id(connection, created.bootstrap_id)
        _require(
            stored is not None, "Caller rollback lost a previously committed bootstrap"
        )
        assert stored is not None
        _require(
            stored.consumed_at is None and stored.revoked_at is None,
            "Lifecycle operation escaped caller rollback",
        )
        with engine.begin() as connection:
            validate_and_consume_bootstrap(
                connection,
                created.bootstrap_value.to_wire(),
                TEST_PEPPER,
                clock=lambda: NOW + timedelta(seconds=3),
            )


def test_concurrent_bootstrap_consumption_commits_exactly_once(
    bootstrap_database: Engine,
) -> None:
    engine = bootstrap_database
    with _safe_database_errors():
        with engine.begin() as connection:
            created = provision_bootstrap(connection, TEST_PEPPER, clock=lambda: NOW)
        ready = Barrier(2)

        def attempt() -> str:
            try:
                with engine.begin() as connection:
                    connection.execute(text("SET SESSION innodb_lock_wait_timeout = 5"))
                    ready.wait(timeout=5)
                    validate_and_consume_bootstrap(
                        connection,
                        created.bootstrap_value.to_wire(),
                        TEST_PEPPER,
                        clock=lambda: NOW + timedelta(seconds=1),
                    )
                return "committed"
            except BootstrapServiceError as failure:
                return (
                    "rejected"
                    if str(failure) == GENERIC_BOOTSTRAP_FAILURE
                    else "unexpected failure"
                )
            except (SQLAlchemyError, BrokenBarrierError, OSError):
                return "database or synchronization failure"

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(attempt) for _ in range(2)]
            results = [future.result(timeout=15) for future in futures]
        _require(
            sorted(results) == ["committed", "rejected"],
            "Concurrent consumption did not produce one commit and one generic rejection",
        )
        with engine.connect() as connection:
            stored = lookup_bootstrap_by_id(connection, created.bootstrap_id)
            count = len(
                connection.execute(select(bootstrap_table.c.bootstrap_id)).all()
            )
        _require(stored is not None, "Concurrent consumption lost the bootstrap record")
        assert stored is not None
        _require(
            count == 1, "Concurrent consumption changed the bootstrap record count"
        )
        _require(
            stored.consumed_at == NOW + timedelta(seconds=1),
            "Concurrent consumption was not durably recorded",
        )
        _require(
            stored.revoked_at is None, "Concurrent consumption changed revocation state"
        )
