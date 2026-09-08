from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta, timezone
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
OTHER_BOOTSTRAP_ID = UUID("2e61b4ca-f0af-4bbc-beb9-43f54b12f353")
MISSING_BOOTSTRAP_ID = UUID("7eed98e3-87f1-4ba9-8aa9-c96dd13b70ea")
UTC_PLUS_0530 = timezone(timedelta(hours=5, minutes=30))


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


def test_insert_normalizes_aware_timestamps_to_utc(connection: Connection) -> None:
    """Catch an insert that stores a wall-clock offset as though it were UTC."""
    created_at = datetime(2026, 9, 8, 9, 0, tzinfo=UTC_PLUS_0530)
    expires_at = created_at + timedelta(minutes=15)

    insert_bootstrap(
        connection,
        make_record(created_at=created_at, expires_at=expires_at),
    )

    stored = lookup_bootstrap_by_id(connection, BOOTSTRAP_ID)
    assert stored is not None
    assert stored.created_at == datetime(2026, 9, 8, 3, 30, tzinfo=UTC)
    assert stored.expires_at == datetime(2026, 9, 8, 3, 45, tzinfo=UTC)


def test_terminal_writes_normalize_aware_timestamps_to_utc(
    connection: Connection,
) -> None:
    """Catch consume or revoke writes that lose the source timestamp offset."""
    other = make_record(
        bootstrap_id=OTHER_BOOTSTRAP_ID,
        lookup_fingerprint=b"f" * 32,
        digest=b"e" * 32,
        operator_label="day-shift",
    )
    insert_bootstrap(connection, make_record())
    insert_bootstrap(connection, other)

    consumed_at = datetime(2026, 9, 8, 9, 1, tzinfo=UTC_PLUS_0530)
    revoked_at = datetime(2026, 9, 8, 9, 2, tzinfo=UTC_PLUS_0530)
    assert consume_bootstrap(connection, BOOTSTRAP_ID, consumed_at)
    assert revoke_bootstrap(connection, OTHER_BOOTSTRAP_ID, revoked_at)

    consumed = lookup_bootstrap_by_id(connection, BOOTSTRAP_ID)
    revoked = lookup_bootstrap_by_id(connection, OTHER_BOOTSTRAP_ID)
    assert consumed is not None
    assert revoked is not None
    assert consumed.consumed_at == datetime(2026, 9, 8, 3, 31, tzinfo=UTC)
    assert revoked.revoked_at == datetime(2026, 9, 8, 3, 32, tzinfo=UTC)


def test_repository_rejects_naive_timestamps_before_writing(
    connection: Connection,
) -> None:
    """Catch timestamp writes that silently assign UTC to a naive input."""
    naive = CREATED_AT.replace(tzinfo=None)

    with pytest.raises(ValueError, match="timestamp must include a timezone"):
        insert_bootstrap(connection, make_record(created_at=naive))

    insert_bootstrap(connection, make_record())
    with pytest.raises(ValueError, match="timestamp must include a timezone"):
        consume_bootstrap(connection, BOOTSTRAP_ID, naive)
    with pytest.raises(ValueError, match="timestamp must include a timezone"):
        revoke_bootstrap(connection, BOOTSTRAP_ID, naive)

    stored = lookup_bootstrap_by_id(connection, BOOTSTRAP_ID)
    assert stored is not None
    assert stored.consumed_at is None
    assert stored.revoked_at is None


def test_lookups_match_only_the_requested_fingerprint_and_bootstrap_id(
    connection: Connection,
) -> None:
    """Catch lookup predicates that return an unrelated bootstrap record."""
    first = make_record()
    second = make_record(
        bootstrap_id=OTHER_BOOTSTRAP_ID,
        lookup_fingerprint=b"f" * 32,
        digest=b"e" * 32,
        operator_label="day-shift",
    )
    insert_bootstrap(connection, first)
    insert_bootstrap(connection, second)

    assert lookup_bootstrap_by_fingerprint(connection, first.lookup_fingerprint) == first
    assert lookup_bootstrap_by_fingerprint(connection, second.lookup_fingerprint) == second
    assert lookup_bootstrap_by_fingerprint(connection, b"z" * 32) is None
    assert lookup_bootstrap_by_id(connection, first.bootstrap_id) == first
    assert lookup_bootstrap_by_id(connection, second.bootstrap_id) == second
    assert lookup_bootstrap_by_id(connection, MISSING_BOOTSTRAP_ID) is None


def test_guarded_updates_target_only_requested_available_bootstraps(
    connection: Connection,
) -> None:
    """Catch terminal updates that touch unrelated, absent, or revoked records."""
    first = make_record()
    second = make_record(
        bootstrap_id=OTHER_BOOTSTRAP_ID,
        lookup_fingerprint=b"f" * 32,
        digest=b"e" * 32,
        operator_label="day-shift",
    )
    insert_bootstrap(connection, first)
    insert_bootstrap(connection, second)

    terminal_at = CREATED_AT + timedelta(minutes=1)
    assert not consume_bootstrap(connection, MISSING_BOOTSTRAP_ID, terminal_at)
    assert not revoke_bootstrap(connection, MISSING_BOOTSTRAP_ID, terminal_at)
    assert lookup_bootstrap_by_id(connection, first.bootstrap_id) == first
    assert lookup_bootstrap_by_id(connection, second.bootstrap_id) == second

    assert consume_bootstrap(connection, first.bootstrap_id, terminal_at)
    assert lookup_bootstrap_by_id(connection, second.bootstrap_id) == second
    assert revoke_bootstrap(connection, second.bootstrap_id, terminal_at)
    assert not consume_bootstrap(connection, second.bootstrap_id, terminal_at)

    consumed = lookup_bootstrap_by_id(connection, first.bootstrap_id)
    revoked = lookup_bootstrap_by_id(connection, second.bootstrap_id)
    assert consumed is not None
    assert revoked is not None
    assert consumed.consumed_at == terminal_at
    assert consumed.revoked_at is None
    assert revoked.consumed_at is None
    assert revoked.revoked_at == terminal_at


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
