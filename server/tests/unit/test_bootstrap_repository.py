from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import Connection
from sqlalchemy.schema import CreateTable
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


class _ExecutionResult:
    def __init__(
        self,
        *,
        row: Mapping[str, object] | None = None,
        rowcount: int = 0,
    ) -> None:
        self._row = row
        self.rowcount = rowcount

    def mappings(self) -> _ExecutionResult:
        return self

    def one_or_none(self) -> Mapping[str, object] | None:
        return self._row


class _RecordingConnection:
    def __init__(self, *results: _ExecutionResult) -> None:
        self.statements: list[ClauseElement] = []
        self._results = deque(results)

    @property
    def sqlalchemy(self) -> Connection:
        return cast(Connection, self)

    def execute(self, statement: ClauseElement) -> _ExecutionResult:
        self.statements.append(statement)
        if self._results:
            return self._results.popleft()
        return _ExecutionResult()

    def commit(self) -> None:
        raise AssertionError("repository operations must not commit")

    def rollback(self) -> None:
        raise AssertionError("repository operations must not roll back")


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


def _database_row(record: BootstrapRecord) -> dict[str, object]:
    def without_timezone(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.astimezone(UTC).replace(tzinfo=None)

    return {
        "bootstrap_id": str(record.bootstrap_id),
        "lookup_fingerprint": record.lookup_fingerprint,
        "digest_version": record.digest_version,
        "digest": record.digest,
        "operator_label": record.operator_label,git ls-files tags
        "created_at": without_timezone(record.created_at),
        "expires_at": without_timezone(record.expires_at),
        "consumed_at": without_timezone(record.consumed_at),
        "revoked_at": without_timezone(record.revoked_at),
    }


def _compiled(statement: ClauseElement) -> tuple[str, dict[str, object]]:
    compiled = statement.compile(dialect=mysql.dialect())
    return str(compiled).lower(), dict(compiled.params)


def test_insert_and_lookups_emit_mysql_statements_and_rehydrate_records() -> None:
    """Catch lost insert values, lookup predicates, or stored-record conversion."""
    expected = make_record()
    insert_connection = _RecordingConnection()

    insert_bootstrap(insert_connection.sqlalchemy, expected)

    insert_sql, insert_params = _compiled(insert_connection.statements[0])
    assert insert_sql.startswith("insert into enrollment_bootstraps")
    assert insert_params == {
        "bootstrap_id": str(expected.bootstrap_id),
        "lookup_fingerprint": expected.lookup_fingerprint,
        "digest_version": expected.digest_version,
        "digest": expected.digest,
        "operator_label": expected.operator_label,
        "created_at": expected.created_at,
        "expires_at": expected.expires_at,
        "consumed_at": None,
        "revoked_at": None,
    }

    lookup_connection = _RecordingConnection(
        _ExecutionResult(row=_database_row(expected)),
        _ExecutionResult(row=_database_row(expected)),
    )
    assert (
        lookup_bootstrap_by_fingerprint(
            lookup_connection.sqlalchemy,
            expected.lookup_fingerprint,
        )
        == expected
    )
    assert lookup_bootstrap_by_id(lookup_connection.sqlalchemy, BOOTSTRAP_ID) == expected

    fingerprint_sql, fingerprint_params = _compiled(lookup_connection.statements[0])
    id_sql, id_params = _compiled(lookup_connection.statements[1])
    assert "where enrollment_bootstraps.lookup_fingerprint" in fingerprint_sql
    assert expected.lookup_fingerprint in fingerprint_params.values()
    assert "where enrollment_bootstraps.bootstrap_id" in id_sql
    assert str(BOOTSTRAP_ID) in id_params.values()


def test_insert_normalizes_aware_timestamps_to_utc() -> None:
    """Catch an insert that stores a wall-clock offset as though it were UTC."""
    created_at = datetime(2026, 9, 8, 9, 0, tzinfo=UTC_PLUS_0530)
    expires_at = created_at + timedelta(minutes=15)
    connection = _RecordingConnection()

    insert_bootstrap(
        connection.sqlalchemy,
        make_record(created_at=created_at, expires_at=expires_at),
    )

    _, params = _compiled(connection.statements[0])
    assert params["created_at"] == datetime(2026, 9, 8, 3, 30, tzinfo=UTC)
    assert params["expires_at"] == datetime(2026, 9, 8, 3, 45, tzinfo=UTC)


def test_terminal_writes_normalize_aware_timestamps_to_utc() -> None:
    """Catch consume or revoke writes that lose the source timestamp offset."""
    connection = _RecordingConnection(
        _ExecutionResult(rowcount=1),
        _ExecutionResult(rowcount=1),
    )
    consumed_at = datetime(2026, 9, 8, 9, 1, tzinfo=UTC_PLUS_0530)
    revoked_at = datetime(2026, 9, 8, 9, 2, tzinfo=UTC_PLUS_0530)

    assert consume_bootstrap(connection.sqlalchemy, BOOTSTRAP_ID, consumed_at)
    assert revoke_bootstrap(connection.sqlalchemy, OTHER_BOOTSTRAP_ID, revoked_at)

    consume_sql, consume_params = _compiled(connection.statements[0])
    revoke_sql, revoke_params = _compiled(connection.statements[1])
    assert "set consumed_at=" in consume_sql
    assert datetime(2026, 9, 8, 3, 31, tzinfo=UTC) in consume_params.values()
    assert "set revoked_at=" in revoke_sql
    assert datetime(2026, 9, 8, 3, 32, tzinfo=UTC) in revoke_params.values()


def test_repository_rejects_naive_timestamps_before_writing() -> None:
    """Catch timestamp writes that silently assign UTC to a naive input."""
    connection = _RecordingConnection()
    naive = CREATED_AT.replace(tzinfo=None)

    with pytest.raises(ValueError, match="timestamp must include a timezone"):
        insert_bootstrap(connection.sqlalchemy, make_record(created_at=naive))
    with pytest.raises(ValueError, match="timestamp must include a timezone"):
        consume_bootstrap(connection.sqlalchemy, BOOTSTRAP_ID, naive)
    with pytest.raises(ValueError, match="timestamp must include a timezone"):
        revoke_bootstrap(connection.sqlalchemy, BOOTSTRAP_ID, naive)

    assert connection.statements == []


def test_lookups_match_only_the_requested_fingerprint_and_bootstrap_id() -> None:
    """Catch lookup predicates that omit or replace the requested key."""
    first = make_record()
    second = make_record(
        bootstrap_id=OTHER_BOOTSTRAP_ID,
        lookup_fingerprint=b"f" * 32,
        digest=b"e" * 32,
        operator_label="day-shift",
    )
    connection = _RecordingConnection(
        _ExecutionResult(row=_database_row(first)),
        _ExecutionResult(row=_database_row(second)),
        _ExecutionResult(),
        _ExecutionResult(row=_database_row(first)),
        _ExecutionResult(row=_database_row(second)),
        _ExecutionResult(),
    )

    assert (
        lookup_bootstrap_by_fingerprint(
            connection.sqlalchemy,
            first.lookup_fingerprint,
        )
        == first
    )
    assert (
        lookup_bootstrap_by_fingerprint(
            connection.sqlalchemy,
            second.lookup_fingerprint,
        )
        == second
    )
    assert lookup_bootstrap_by_fingerprint(connection.sqlalchemy, b"z" * 32) is None
    assert lookup_bootstrap_by_id(connection.sqlalchemy, first.bootstrap_id) == first
    assert lookup_bootstrap_by_id(connection.sqlalchemy, second.bootstrap_id) == second
    assert lookup_bootstrap_by_id(connection.sqlalchemy, MISSING_BOOTSTRAP_ID) is None

    expected_parameters = (
        first.lookup_fingerprint,
        second.lookup_fingerprint,
        b"z" * 32,
        str(first.bootstrap_id),
        str(second.bootstrap_id),
        str(MISSING_BOOTSTRAP_ID),
    )
    for statement, expected_parameter in zip(
        connection.statements,
        expected_parameters,
        strict=True,
    ):
        _, params = _compiled(statement)
        assert expected_parameter in params.values()


def test_guarded_updates_target_only_requested_available_bootstraps() -> None:
    """Catch terminal updates that omit their ID or availability guards."""
    connection = _RecordingConnection(
        _ExecutionResult(rowcount=0),
        _ExecutionResult(rowcount=0),
        _ExecutionResult(rowcount=1),
        _ExecutionResult(rowcount=1),
        _ExecutionResult(rowcount=0),
    )
    terminal_at = CREATED_AT + timedelta(minutes=1)

    assert not consume_bootstrap(connection.sqlalchemy, MISSING_BOOTSTRAP_ID, terminal_at)
    assert not revoke_bootstrap(connection.sqlalchemy, MISSING_BOOTSTRAP_ID, terminal_at)
    assert consume_bootstrap(connection.sqlalchemy, BOOTSTRAP_ID, terminal_at)
    assert revoke_bootstrap(connection.sqlalchemy, OTHER_BOOTSTRAP_ID, terminal_at)
    assert not consume_bootstrap(connection.sqlalchemy, OTHER_BOOTSTRAP_ID, terminal_at)

    expected_ids = (
        MISSING_BOOTSTRAP_ID,
        MISSING_BOOTSTRAP_ID,
        BOOTSTRAP_ID,
        OTHER_BOOTSTRAP_ID,
        OTHER_BOOTSTRAP_ID,
    )
    for statement, expected_id in zip(connection.statements, expected_ids, strict=True):
        sql, params = _compiled(statement)
        assert "consumed_at is null" in sql
        assert "revoked_at is null" in sql
        assert str(expected_id) in params.values()


def test_fingerprint_lookup_can_request_a_mysql_row_lock() -> None:
    """Catch a consumption lookup that silently drops the requested row lock."""
    expected = make_record()
    connection = _RecordingConnection(_ExecutionResult(row=_database_row(expected)))

    found = lookup_bootstrap_by_fingerprint(
        connection.sqlalchemy,
        expected.lookup_fingerprint,
        for_update=True,
    )

    assert found == expected
    compiled, _ = _compiled(connection.statements[0])
    assert "for update" in compiled


def test_id_lookup_can_request_a_mysql_row_lock() -> None:
    """Catch a revocation lookup that silently drops the requested row lock."""
    expected = make_record()
    connection = _RecordingConnection(_ExecutionResult(row=_database_row(expected)))

    found = lookup_bootstrap_by_id(
        connection.sqlalchemy,
        BOOTSTRAP_ID,
        for_update=True,
    )

    assert found == expected
    compiled, _ = _compiled(connection.statements[0])
    assert "for update" in compiled


def test_lookup_fingerprint_has_a_mysql_unique_constraint() -> None:
    """Catch removal of the unique lookup-fingerprint database constraint."""
    ddl = " ".join(
        str(CreateTable(bootstrap_table).compile(dialect=mysql.dialect()))
        .lower()
        .split()
    )

    assert "unique (lookup_fingerprint)" in ddl


def test_guarded_consume_updates_only_an_available_bootstrap() -> None:
    """Catch a consume update that can overwrite a terminal transition."""
    connection = _RecordingConnection(
        _ExecutionResult(rowcount=1),
        _ExecutionResult(rowcount=0),
    )
    consumed_at = CREATED_AT + timedelta(minutes=1)

    assert consume_bootstrap(connection.sqlalchemy, BOOTSTRAP_ID, consumed_at)
    assert not consume_bootstrap(
        connection.sqlalchemy,
        BOOTSTRAP_ID,
        consumed_at + timedelta(minutes=1),
    )

    for statement in connection.statements:
        sql, _ = _compiled(statement)
        assert "consumed_at is null" in sql
        assert "revoked_at is null" in sql


def test_guarded_revoke_does_not_replace_consumption() -> None:
    """Catch a revoke update that can replace a prior consumption transition."""
    connection = _RecordingConnection(_ExecutionResult(rowcount=0))

    assert not revoke_bootstrap(
        connection.sqlalchemy,
        BOOTSTRAP_ID,
        CREATED_AT + timedelta(minutes=2),
    )

    sql, _ = _compiled(connection.statements[0])
    assert "consumed_at is null" in sql
    assert "revoked_at is null" in sql


def test_guarded_revoke_updates_an_available_bootstrap_once() -> None:
    """Catch a revoke update that misses an available row or overwrites itself."""
    connection = _RecordingConnection(
        _ExecutionResult(rowcount=1),
        _ExecutionResult(rowcount=0),
    )
    revoked_at = CREATED_AT + timedelta(minutes=1)

    assert revoke_bootstrap(connection.sqlalchemy, BOOTSTRAP_ID, revoked_at)
    assert not revoke_bootstrap(
        connection.sqlalchemy,
        BOOTSTRAP_ID,
        revoked_at + timedelta(minutes=1),
    )

    for statement in connection.statements:
        sql, _ = _compiled(statement)
        assert "consumed_at is null" in sql
        assert "revoked_at is null" in sql


def test_repository_leaves_transactions_owned_by_the_caller() -> None:
    """Catch a repository operation that commits or rolls back its caller's work."""
    connection = _RecordingConnection(_ExecutionResult(row=_database_row(make_record())))

    insert_bootstrap(connection.sqlalchemy, make_record())
    assert lookup_bootstrap_by_id(connection.sqlalchemy, BOOTSTRAP_ID) == make_record()

    assert len(connection.statements) == 2
