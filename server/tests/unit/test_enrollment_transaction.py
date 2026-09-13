"""Enrollment ordering/error contracts; real transaction semantics need MySQL."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from unittest.mock import Mock

import pytest
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.dml import Insert

from device_watch_server.auth.credentials import CredentialRecord, verify_credential
from device_watch_server.enrollment import transaction
from device_watch_server.enrollment.bootstrap import generate_bootstrap_value
from device_watch_server.enrollment.service import BootstrapServiceError
from device_watch_server.enrollment.transaction import EnrollmentError, enroll_device

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
PEPPER = "unit-fixture-enrollment-pepper-not-for-deployment"


class TransactionBoundary:
    """Capture real persistence statements and simulate commit/rollback failures."""

    def __init__(self, failure: str | None = None) -> None:
        self.failure = failure
        self.events: list[str] = []
        self.pending: list[tuple[str, dict[str, object]]] = []
        self.committed: list[tuple[str, dict[str, object]]] = []
        self.connection = Mock(spec_set=Connection)
        self.connection.execute.side_effect = self.execute

    def execute(self, statement: Insert) -> None:
        name = statement.table.name
        params = dict(statement.compile(dialect=mysql.dialect()).params)
        self.pending.append((name, params))
        self.events.append(name)
        if self.failure == name:
            raise SQLAlchemyError("database details must not escape")

    @contextmanager
    def begin(self) -> Iterator[Connection]:
        self.events.append("begin")
        try:
            if self.failure == "begin":
                raise SQLAlchemyError("connection details must not escape")
            yield self.connection
            if self.failure == "commit":
                raise SQLAlchemyError("commit details must not escape")
        except Exception:
            self.pending.clear()
            self.events.append("rollback")
            raise
        else:
            self.committed.extend(self.pending)
            self.pending.clear()
            self.events.append("commit")


@pytest.fixture
def claim(monkeypatch: pytest.MonkeyPatch) -> list[Connection]:
    seen: list[Connection] = []

    def capture_claim(
        connection: Connection, wire_value: str, configured_pepper: str | None,
        *, clock: transaction.Clock,
    ) -> None:
        seen.append(connection)
        assert configured_pepper == PEPPER
        clock()

    monkeypatch.setattr(transaction, "validate_and_consume_bootstrap", capture_claim)
    return seen


def test_enrollment_commits_identity_and_hash_before_returning_secret(
    claim: list[Connection], caplog: pytest.LogCaptureFixture,
) -> None:
    boundary = TransactionBoundary()
    bootstrap = generate_bootstrap_value()
    with caplog.at_level(logging.INFO):
        result = enroll_device(
            cast(Engine, boundary), bootstrap.to_wire(), PEPPER,
            display_name="  workstation  ", clock=lambda: NOW.replace(microsecond=765432),
        )

    assert claim == [boundary.connection]
    assert boundary.events == ["begin", "devices", "device_credentials", "commit"]
    assert result.device.device_id.version == 4
    assert result.device.display_name == "workstation"
    assert result.device.created_at == NOW
    assert len(boundary.committed) == 2
    device_values = boundary.committed[0][1]
    credential_values = boundary.committed[1][1]
    assert set(device_values) == {"device_id", "display_name", "created_at", "lifecycle"}
    assert device_values["device_id"] == str(result.device.device_id)
    assert device_values["lifecycle"] == "active"
    assert set(credential_values) == {
        "key_id", "device_id", "secret_hash", "created_at",
        "last_used_at", "revoked_at", "replaced_at",
    }
    assert credential_values["device_id"] == device_values["device_id"]
    assert credential_values["created_at"] == device_values["created_at"]
    assert credential_values["last_used_at"] is None
    assert credential_values["revoked_at"] is None
    assert credential_values["replaced_at"] is None
    stored = CredentialRecord(
        key_id=cast(str, credential_values["key_id"]),
        secret_hash=cast(str, credential_values["secret_hash"]), created_at=NOW,
    )
    assert verify_credential(result.credential.to_wire(), stored)
    assert set(vars(result)) == {"device", "credential"}
    safe_persistence = all(value not in repr(boundary.committed) for value in (
        result.credential.to_wire(), bootstrap.to_wire(),
    ))
    assert safe_persistence
    representation = repr(result) + str(result) + caplog.text
    safe_output = all(value not in representation for value in (
        result.credential.to_wire(), stored.secret_hash, bootstrap.to_wire(),
    ))
    assert safe_output


@pytest.mark.parametrize("failure", ("begin", "devices", "device_credentials", "commit"))
def test_database_failures_do_not_return_a_result_and_roll_back(
    claim: list[Connection], failure: str,
) -> None:
    boundary = TransactionBoundary(failure)
    with pytest.raises(EnrollmentError) as error:
        enroll_device(
            cast(Engine, boundary), generate_bootstrap_value().to_wire(), PEPPER,
            display_name="workstation", clock=lambda: NOW,
        )
    assert str(error.value) == "Enrollment failed"
    assert error.value.__suppress_context__
    assert boundary.events[-1] == "rollback"
    assert boundary.committed == []
    assert boundary.pending == []
    assert boundary.events.count("begin") == 1


def test_invalid_bootstrap_does_not_issue_or_persist_any_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary = TransactionBoundary()

    def reject(*args: object, **kwargs: object) -> None:
        raise BootstrapServiceError()

    def forbidden_issue(*args: object, **kwargs: object) -> None:
        pytest.fail("Invalid bootstrap triggered credential issuance")

    monkeypatch.setattr(transaction, "validate_and_consume_bootstrap", reject)
    monkeypatch.setattr(transaction, "issue_credential", forbidden_issue)
    with pytest.raises(EnrollmentError, match="^Enrollment failed$"):
        enroll_device(
            cast(Engine, boundary), "invalid", PEPPER, display_name="workstation",
        )
    assert boundary.events == ["begin", "rollback"]
    assert boundary.committed == []


@pytest.mark.parametrize("display_name", ("", " ", "x" * 121))
def test_invalid_identity_rolls_back_bootstrap_claim(
    claim: list[Connection], display_name: str,
) -> None:
    boundary = TransactionBoundary()
    with pytest.raises(EnrollmentError, match="^Enrollment failed$"):
        enroll_device(
            cast(Engine, boundary), generate_bootstrap_value().to_wire(), PEPPER,
            display_name=display_name, clock=lambda: NOW,
        )
    assert boundary.events[-1] == "rollback"
    assert boundary.committed == []


def test_hash_failure_is_sanitized_and_prevents_commit(
    claim: list[Connection], monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary = TransactionBoundary()
    bootstrap = generate_bootstrap_value()

    def fail_hash(*args: object, **kwargs: object) -> None:
        raise RuntimeError(bootstrap.to_wire() + PEPPER)

    monkeypatch.setattr(transaction, "issue_credential", fail_hash)
    with pytest.raises(EnrollmentError) as error:
        enroll_device(
            cast(Engine, boundary), bootstrap.to_wire(), PEPPER,
            display_name="workstation", clock=lambda: NOW,
        )
    assert str(error.value) == "Enrollment failed"
    assert error.value.__suppress_context__
    assert boundary.events[-1] == "rollback"
    assert boundary.committed == []


def test_service_preserves_live_clock_for_post_lock_bootstrap_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary = TransactionBoundary()
    current = NOW

    def clock() -> datetime:
        return current

    def delayed_claim(
        connection: Connection, wire_value: str, configured_pepper: str | None,
        *, clock: transaction.Clock,
    ) -> None:
        nonlocal current
        current = NOW + timedelta(minutes=1)
        assert clock() == current
        raise BootstrapServiceError()

    monkeypatch.setattr(transaction, "validate_and_consume_bootstrap", delayed_claim)
    with pytest.raises(EnrollmentError):
        enroll_device(
            cast(Engine, boundary), generate_bootstrap_value().to_wire(), PEPPER,
            display_name="workstation", clock=clock,
        )
    assert boundary.committed == []


def test_utc_timestamp_normalization_and_naive_rejection(claim: list[Connection]) -> None:
    boundary = TransactionBoundary()
    offset = NOW.astimezone(timezone(timedelta(hours=5, minutes=30)))
    result = enroll_device(
        cast(Engine, boundary), generate_bootstrap_value().to_wire(), PEPPER,
        display_name="workstation", clock=lambda: offset,
    )
    assert result.device.created_at == NOW
    assert result.device.created_at.tzinfo is UTC
    with pytest.raises(EnrollmentError):
        enroll_device(
            cast(Engine, boundary), generate_bootstrap_value().to_wire(), PEPPER,
            display_name="workstation", clock=lambda: NOW.replace(tzinfo=None),
        )
