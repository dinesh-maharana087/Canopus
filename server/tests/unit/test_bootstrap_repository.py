from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.elements import ClauseElement

from device_watch_server.enrollment.bootstrap import DIGEST_VERSION
from device_watch_server.enrollment.repository import (
    BootstrapRecord,
    bootstrap_table,
    consume_bootstrap,
    insert_bootstrap,
    lookup_bootstrap_by_fingerprint,
    lookup_bootstrap_by_id,
    revoke_bootstrap,
)

CREATED_AT = datetime(2026, 9, 8, 9, 0, tzinfo=UTC)
BOOTSTRAP_ID = UUID("c919f0d6-17a7-4b4c-b579-e1cc4ce2bb03")


@pytest.fixture
def connection() -> Generator[Connection, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    bootstrap_table.create(engine)
    with engine.connect() as connection:
        yield connection
    engine.dispose()


def make_record(**changes: object) -> BootstrapRecord:
    values: dict[str, object] = {
        "bootstrap_id": BOOTSTRAP_ID,
        "lookup_fingerprint": bytes(range(32)),
        "digest_version": DIGEST_VERSION,
        "digest": b"d" * 32,
        "operator_label": "night-shift",
        "created_at": CREATED_AT,
        "expires_at": CREATED_AT + timedelta(minutes=15),
        "consumed_at": None,
        "revoked_at": None,
    }
    values.update(changes)
    return BootstrapRecord(**values)  # type: ignore[arg-type]


def test_insert_and_lookups_round_trip_binary_material_and_utc_timestamps(
    connection: Connection,
) -> None:
    """Catch a repository that loses stored bootstrap data or UTC audit timestamps."""
    expected = make_record()

    insert_bootstrap(connection, expected)

    assert lookup_bootstrap_by_fingerprint(connection, bytes(range(32))) == expected
    assert lookup_bootstrap_by_id(connection, BOOTSTRAP_ID) == expected


def test_fingerprint_lookup_can_request_a_mysql_row_lock(connection: Connection) -> None:
    """Catch a consumption lookup that silently drops the requested row lock."""
    insert_bootstrap(connection, make_record())
    statements: list[ClauseElement] = []

    def capture_statement(*args: object) -> None:
        statements.append(cast(ClauseElement, args[1]))

    event.listen(connection, "before_execute", capture_statement)
    try:
        found = lookup_bootstrap_by_fingerprint(
            connection, bytes(range(32)), for_update=True
        )
    finally:
        event.remove(connection, "before_execute", capture_statement)

    assert found is not None
    compiled = str(statements[-1].compile(dialect=mysql.dialect())).lower()
    assert "for update" in compiled


def test_duplicate_lookup_fingerprint_is_rejected(connection: Connection) -> None:
    """Catch removal of the unique lookup-fingerprint database constraint."""
    insert_bootstrap(connection, make_record())

    with pytest.raises(IntegrityError):
        insert_bootstrap(
            connection,
            make_record(bootstrap_id=UUID("2e61b4ca-f0af-4bbc-beb9-43f54b12f353")),
        )


def test_guarded_consume_updates_only_an_available_bootstrap(
    connection: Connection,
) -> None:
    """Catch a consume update that overwrites an existing terminal transition."""
    insert_bootstrap(connection, make_record())
    consumed_at = CREATED_AT + timedelta(minutes=1)

    assert consume_bootstrap(connection, BOOTSTRAP_ID, consumed_at)
    assert not consume_bootstrap(connection, BOOTSTRAP_ID, consumed_at + timedelta(minutes=1))

    stored = lookup_bootstrap_by_id(connection, BOOTSTRAP_ID)
    assert stored is not None
    assert stored.consumed_at == consumed_at
    assert stored.revoked_at is None


def test_guarded_revoke_does_not_replace_consumption(connection: Connection) -> None:
    """Catch a revoke update that can replace a prior consumption transition."""
    insert_bootstrap(connection, make_record())
    consumed_at = CREATED_AT + timedelta(minutes=1)

    assert consume_bootstrap(connection, BOOTSTRAP_ID, consumed_at)
    assert not revoke_bootstrap(connection, BOOTSTRAP_ID, consumed_at + timedelta(minutes=1))

    stored = lookup_bootstrap_by_id(connection, BOOTSTRAP_ID)
    assert stored is not None
    assert stored.consumed_at == consumed_at
    assert stored.revoked_at is None


def test_guarded_revoke_updates_an_available_bootstrap_once(
    connection: Connection,
) -> None:
    """Catch a revoke update that misses an available row or overwrites itself."""
    insert_bootstrap(connection, make_record())
    revoked_at = CREATED_AT + timedelta(minutes=1)

    assert revoke_bootstrap(connection, BOOTSTRAP_ID, revoked_at)
    assert not revoke_bootstrap(connection, BOOTSTRAP_ID, revoked_at + timedelta(minutes=1))

    stored = lookup_bootstrap_by_id(connection, BOOTSTRAP_ID)
    assert stored is not None
    assert stored.consumed_at is None
    assert stored.revoked_at == revoked_at


def test_repository_leaves_the_callers_transaction_open(connection: Connection) -> None:
    """Catch a repository operation that commits its caller-owned transaction."""
    transaction = connection.begin()

    insert_bootstrap(connection, make_record())
    transaction.rollback()

    assert lookup_bootstrap_by_id(connection, BOOTSTRAP_ID) is None
