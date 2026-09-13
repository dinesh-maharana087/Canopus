"""Step 05 against an empty, dedicated disposable MySQL 8.x database.

Run serially with DEVICE_WATCH_ENV=test, DATABASE_URL from protected configuration,
and DEVICE_WATCH_DISPOSABLE_DATABASE=1. Never share this database with another
suite/application. Unknown schema/revisions and pre-existing rows are refused
before mutation. Only this module's rows are cleared; revision 0004 remains.
Missing DATABASE_URL skips the shared fixture without opening a connection.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from threading import Barrier, Event
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.util.exc import CommandError
from sqlalchemy import event, inspect, select, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from alembic import command
from device_watch_server.auth.credentials import CredentialRecord, verify_credential
from device_watch_server.core.config import Environment, load_settings
from device_watch_server.db.engine import create_database_engine
from device_watch_server.enrollment import transaction
from device_watch_server.enrollment.persistence import credentials_table, devices_table
from device_watch_server.enrollment.repository import bootstrap_table
from device_watch_server.enrollment.service import provision_bootstrap
from device_watch_server.enrollment.transaction import (
    EnrollmentError,
    EnrollmentResult,
    enroll_device,
)

pytestmark = pytest.mark.integration
BOOTSTRAP_REVISION = "20260908_0003"
ENROLLMENT_REVISION = "20260913_0004"
NOW = datetime(2026, 9, 13, 12, tzinfo=UTC)
TEST_PEPPER = "enrollment-integration-fixture-pepper-minimum-32-bytes"
_TABLES = (credentials_table, bootstrap_table, devices_table)
_REVISION_TABLES = {
    "20260831_0001": {"alembic_version"},
    "20260908_0002": {"alembic_version", "devices"},
    BOOTSTRAP_REVISION: {"alembic_version", "devices", "enrollment_bootstraps"},
    ENROLLMENT_REVISION: {
        "alembic_version",
        "devices",
        "enrollment_bootstraps",
        "device_credentials",
    },
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        pytest.fail(message, pytrace=False)


@contextmanager
def _safe_database_errors() -> Iterator[None]:
    try:
        yield
    except SQLAlchemyError:
        pytest.fail("Enrollment database check failed; details withheld", pytrace=False)


def _known_revision(connection: Connection) -> str | None:
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    _require(not inspector.get_view_names(), "Refusing a database containing views")
    _require(
        tables <= _REVISION_TABLES[ENROLLMENT_REVISION],
        "Refusing tables outside the enrollment test allowlist",
    )
    if "alembic_version" not in tables:
        _require(not tables, "Refusing an unversioned nonempty schema")
        return None
    revisions = connection.execute(text("SELECT version_num FROM alembic_version"))
    versions = revisions.scalars().all()
    if not versions:
        _require(tables == {"alembic_version"}, "Refusing an inconsistent base schema")
        return None
    _require(len(versions) == 1, "Refusing multiple migration heads")
    revision = str(versions[0])
    _require(revision in _REVISION_TABLES, "Refusing an unknown migration revision")
    _require(tables == _REVISION_TABLES[revision], "Refusing an inconsistent schema")
    return revision


def _migrate(engine: Engine, revision: str, *, downgrade: bool = False) -> None:
    with _safe_database_errors(), engine.connect() as connection:
        _known_revision(connection)
    try:
        operation = command.downgrade if downgrade else command.upgrade
        operation(Config("server/alembic.ini"), revision)
    except (CommandError, SQLAlchemyError, ValueError, OSError):
        pytest.fail("Enrollment migration failed; details withheld", pytrace=False)


@pytest.fixture(scope="module")
def mysql_engine() -> Iterator[Engine]:
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not configured for enrollment MySQL tests")
    _require(
        os.environ.get("DEVICE_WATCH_ENV") == "test"
        and os.environ.get("DEVICE_WATCH_DISPOSABLE_DATABASE") == "1",
        "Require DEVICE_WATCH_ENV=test and DEVICE_WATCH_DISPOSABLE_DATABASE=1",
    )
    try:
        settings = load_settings()
        _require(
            settings.device_watch_env is Environment.TEST, "Refusing non-test mode"
        )
        engine = create_database_engine(settings)
    except (ValueError, SQLAlchemyError, OSError):
        pytest.fail(
            "Enrollment test configuration failed; details withheld", pytrace=False
        )
    try:
        with _safe_database_errors(), engine.connect() as connection:
            version = str(connection.execute(text("SELECT VERSION()")).scalar_one())
            _require(version.startswith("8."), "Enrollment tests require MySQL 8.x")
            _known_revision(connection)
            existing = set(inspect(connection).get_table_names())
            for table in _TABLES:
                if table.name in existing:
                    _require(
                        connection.execute(select(table).limit(1)).first() is None,
                        "Refusing pre-existing rows in the disposable database",
                    )
        _migrate(engine, ENROLLMENT_REVISION)
        with _safe_database_errors(), engine.connect() as connection:
            engines = (
                connection.execute(
                    text(
                        "SELECT ENGINE FROM information_schema.TABLES "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN "
                        "('devices', 'enrollment_bootstraps', 'device_credentials')"
                    )
                )
                .scalars()
                .all()
            )
            _require(
                len(engines) == 3 and all(value == "InnoDB" for value in engines),
                "All enrollment tables must use transactional InnoDB storage",
            )
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def enrollment_database(mysql_engine: Engine) -> Iterator[Engine]:
    yield mysql_engine
    with _safe_database_errors(), mysql_engine.begin() as connection:
        for table in _TABLES:
            connection.execute(table.delete())


def _bootstrap(engine: Engine, *, expires_in_minutes: int = 15) -> str:
    with _safe_database_errors(), engine.begin() as connection:
        return provision_bootstrap(
            connection,
            TEST_PEPPER,
            expires_in_minutes=expires_in_minutes,
            clock=lambda: NOW,
        ).bootstrap_value.to_wire()


def _enroll(
    engine: Engine, bootstrap: str, *, clock: Callable[[], datetime] = lambda: NOW
) -> EnrollmentResult:
    return enroll_device(
        engine, bootstrap, TEST_PEPPER, display_name="integration device", clock=clock
    )


def _counts(engine: Engine) -> tuple[int, int, int]:
    with _safe_database_errors(), engine.connect() as connection:
        devices, credentials, consumed = (
            int(connection.execute(text(query)).scalar_one())
            for query in (
                "SELECT COUNT(*) FROM devices",
                "SELECT COUNT(*) FROM device_credentials",
                "SELECT COUNT(*) FROM enrollment_bootstraps WHERE consumed_at IS NOT NULL",
            )
        )
        return devices, credentials, consumed


def test_enrollment_commits_hash_only_and_rejects_credential_replay(
    enrollment_database: Engine,
) -> None:
    engine = enrollment_database
    bootstrap = _bootstrap(engine)
    result = _enroll(engine, bootstrap)
    _require(
        _counts(engine) == (1, 1, 1), "Enrollment did not commit exactly one identity"
    )
    with _safe_database_errors(), engine.connect() as connection:
        row = connection.execute(select(credentials_table)).mappings().one()
        device = connection.execute(select(devices_table)).mappings().one()
        _require(
            row["device_id"] == str(result.device.device_id)
            and device["device_id"] == row["device_id"],
            "Persisted identity and credential ownership do not match",
        )
        stored = CredentialRecord(
            key_id=row["key_id"],
            secret_hash=row["secret_hash"],
            created_at=row["created_at"].replace(tzinfo=UTC),
        )
        _require(
            verify_credential(result.credential.to_wire(), stored),
            "Persisted credential hash does not verify the issued credential",
        )
        _require(
            all(
                row[name] is None
                for name in ("last_used_at", "revoked_at", "replaced_at")
            ),
            "New credential unexpectedly has lifecycle timestamps",
        )
        _require(
            result.device.created_at == device["created_at"].replace(tzinfo=UTC),
            "Returned timestamp differs from persisted server timestamp",
        )
        _require(
            result.credential.to_wire() not in repr(row)
            and bootstrap not in repr(row)
            and row["secret_hash"] not in repr(result)
            and result.credential.to_wire() not in repr(result),
            "Enrollment plaintext or hash escaped its intended boundary",
        )
    with pytest.raises(EnrollmentError, match="^Enrollment failed$"):
        _enroll(engine, bootstrap)
    _require(
        _counts(engine) == (1, 1, 1), "Replay created another identity or credential"
    )


def test_concurrent_enrollment_has_exactly_one_committed_winner(
    enrollment_database: Engine,
) -> None:
    engine = enrollment_database
    bootstrap = _bootstrap(engine)
    barrier = Barrier(4)

    def attempt() -> bool:
        barrier.wait(timeout=10)
        try:
            _enroll(engine, bootstrap)
            return True
        except EnrollmentError as error:
            _require(
                str(error) == "Enrollment failed", "Concurrent failure leaked details"
            )
            return False

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(attempt) for _ in range(4)]
        winners = sum(future.result(timeout=30) for future in futures)
    _require(winners == 1, "Concurrent enrollment did not have exactly one winner")
    _require(
        _counts(engine) == (1, 1, 1), "Concurrent enrollment left duplicate effects"
    )


@pytest.mark.parametrize("failure_point", ["insert_device", "insert_credential"])
def test_insert_failure_rolls_back_all_enrollment_effects(
    enrollment_database: Engine, monkeypatch: pytest.MonkeyPatch, failure_point: str
) -> None:
    engine = enrollment_database
    bootstrap = _bootstrap(engine)
    original = getattr(transaction, failure_point)

    def fail_after_insert(*args: object, **kwargs: object) -> None:
        original(*args, **kwargs)
        raise RuntimeError("injected enrollment insert failure")

    with monkeypatch.context() as patch:
        patch.setattr(transaction, failure_point, fail_after_insert)
        with pytest.raises(EnrollmentError, match="^Enrollment failed$"):
            _enroll(engine, bootstrap)
    _require(_counts(engine) == (0, 0, 0), "Failed enrollment left committed effects")
    _enroll(engine, bootstrap)
    _require(_counts(engine) == (1, 1, 1), "Rolled-back bootstrap cannot enroll again")


def test_bootstrap_expiring_while_waiting_for_lock_is_rejected(
    enrollment_database: Engine,
) -> None:
    engine = enrollment_database
    bootstrap = _bootstrap(engine, expires_in_minutes=1)
    selecting = Event()
    current = [NOW + timedelta(seconds=59)]

    def observe_select(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        if "enrollment_bootstraps" in statement and "FOR UPDATE" in statement.upper():
            selecting.set()

    listener_added = False
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            with engine.begin() as lock:
                lock.execute(select(bootstrap_table).with_for_update()).all()
                event.listen(engine, "before_cursor_execute", observe_select)
                listener_added = True
                future = executor.submit(
                    _enroll, engine, bootstrap, clock=lambda: current[0]
                )
                _require(
                    selecting.wait(timeout=5), "Enrollment never attempted the row lock"
                )
                current[0] = NOW + timedelta(minutes=1)
            with pytest.raises(EnrollmentError, match="^Enrollment failed$"):
                future.result(timeout=30)
    finally:
        if listener_added:
            event.remove(engine, "before_cursor_execute", observe_select)
    _require(
        _counts(engine) == (0, 0, 0), "Expired bootstrap acquired enrollment effects"
    )


def test_credential_migration_round_trip_and_database_constraints(
    enrollment_database: Engine,
) -> None:
    engine = enrollment_database
    _migrate(engine, BOOTSTRAP_REVISION, downgrade=True)
    with _safe_database_errors(), engine.connect() as connection:
        _require(_known_revision(connection) == BOOTSTRAP_REVISION, "Downgrade failed")
    _migrate(engine, ENROLLMENT_REVISION)
    with _safe_database_errors(), engine.connect() as connection:
        inspector = inspect(connection)
        columns = {
            item["name"]: item for item in inspector.get_columns("device_credentials")
        }
        _require(
            set(columns)
            == {
                "key_id",
                "device_id",
                "secret_hash",
                "created_at",
                "last_used_at",
                "revoked_at",
                "replaced_at",
            },
            "Credential storage has missing or unexpected fields",
        )
        _require(
            inspector.get_pk_constraint("device_credentials")["constrained_columns"]
            == ["key_id"],
            "Credential lookup identifier is not the primary key",
        )
        _require(
            all(
                not columns[name]["nullable"]
                for name in ("key_id", "device_id", "secret_hash", "created_at")
            ),
            "Required credential fields are nullable",
        )
        _require(
            all(
                getattr(columns[name]["type"], "length", None) == length
                for name, length in (
                    ("key_id", 32),
                    ("device_id", 36),
                    ("secret_hash", 97),
                )
            ),
            "Credential column lengths violate the persistence contract",
        )
        _require(
            any(
                item["column_names"] == ["device_id"] and not item["unique"]
                for item in inspector.get_indexes("device_credentials")
            ),
            "Credential device lookup needs a nonunique index",
        )
    result = _enroll(engine, _bootstrap(engine))
    with _safe_database_errors(), engine.begin() as connection:
        values = dict(connection.execute(select(credentials_table)).mappings().one())
        invalid_changes: tuple[dict[str, object], ...] = (
            {},
            {"key_id": uuid4().hex, "device_id": str(uuid4())},
            {"key_id": uuid4().hex, "revoked_at": NOW - timedelta(seconds=1)},
            {"key_id": uuid4().hex, "last_used_at": NOW - timedelta(seconds=1)},
            {"key_id": uuid4().hex, "replaced_at": NOW},
        )
        for changes in invalid_changes:
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(credentials_table.insert().values(values | changes))
        connection.execute(
            credentials_table.insert().values(
                values
                | {"key_id": uuid4().hex, "device_id": str(result.device.device_id)}
            )
        )
    _require(
        _counts(engine) == (1, 2, 1),
        "Credential foreign key incorrectly forbids rotation",
    )
