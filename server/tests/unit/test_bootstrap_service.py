from __future__ import annotations

from collections.abc import Generator
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy.engine import Connection

from device_watch_server.core.config import Environment, Settings, load_settings
from device_watch_server.enrollment import service
from device_watch_server.enrollment.bootstrap import (
    DIGEST_VERSION,
    BootstrapValue,
    bootstrap_fingerprint,
    verify_bootstrap_digest,
)
from device_watch_server.enrollment.repository import BootstrapRecord
from device_watch_server.enrollment.service import (
    DEFAULT_BOOTSTRAP_EXPIRY_MINUTES,
    BootstrapServiceError,
    provision_bootstrap,
    revoke_bootstrap,
    validate_and_consume_bootstrap,
)

DATABASE_URL = "mysql+pymysql://service_user:service_password@db/device_watch"
HMAC_PEPPER = "bootstrap-pepper-material-32-bytes-minimum"
OTHER_HMAC_PEPPER = "different-pepper-material-32-bytes-minimum"
NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
UTC_PLUS_0530 = timezone(timedelta(hours=5, minutes=30))
UNKNOWN_WIRE_VALUE = "dwb_v1_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


@pytest.fixture
def connection() -> Generator[Connection, None, None]:
    boundary = Mock(spec_set=Connection)
    yield cast(Connection, boundary)
    boundary.begin.assert_not_called()
    boundary.commit.assert_not_called()
    boundary.rollback.assert_not_called()
    boundary.execute.assert_not_called()


class _RepositoryDouble:
    """Supply repository results; SQL and guards are tested at their own boundary."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection
        self.records: dict[UUID, BootstrapRecord] = {}
        self.calls: list[tuple[str, UUID | bytes, bool | datetime]] = []

    def insert(self, connection: Connection, record: BootstrapRecord) -> None:
        assert connection is self.connection
        self.records[record.bootstrap_id] = record

    def by_fingerprint(
        self, connection: Connection, fingerprint: bytes, *, for_update: bool = False
    ) -> BootstrapRecord | None:
        assert connection is self.connection
        self.calls.append(("fingerprint", fingerprint, for_update))
        return next(
            (r for r in self.records.values() if r.lookup_fingerprint == fingerprint),
            None,
        )

    def by_id(
        self, connection: Connection, bootstrap_id: UUID, *, for_update: bool = False
    ) -> BootstrapRecord | None:
        assert connection is self.connection
        self.calls.append(("id", bootstrap_id, for_update))
        return self.records.get(bootstrap_id)

    def consume(
        self, connection: Connection, bootstrap_id: UUID, consumed_at: datetime
    ) -> bool:
        assert connection is self.connection
        self.calls.append(("consume", bootstrap_id, consumed_at))
        self.records[bootstrap_id] = replace(
            self.records[bootstrap_id], consumed_at=consumed_at
        )
        return True

    def revoke(
        self, connection: Connection, bootstrap_id: UUID, revoked_at: datetime
    ) -> bool:
        assert connection is self.connection
        self.calls.append(("revoke", bootstrap_id, revoked_at))
        self.records[bootstrap_id] = replace(
            self.records[bootstrap_id], revoked_at=revoked_at
        )
        return True


@pytest.fixture
def repository(
    connection: Connection, monkeypatch: pytest.MonkeyPatch
) -> _RepositoryDouble:
    boundary = _RepositoryDouble(connection)
    monkeypatch.setattr(service, "insert_bootstrap", boundary.insert)
    monkeypatch.setattr(service, "lookup_bootstrap_by_fingerprint", boundary.by_fingerprint)
    monkeypatch.setattr(service, "lookup_bootstrap_by_id", boundary.by_id)
    monkeypatch.setattr(service, "mark_bootstrap_consumed", boundary.consume)
    monkeypatch.setattr(service, "mark_bootstrap_revoked", boundary.revoke)
    return boundary


def test_bootstrap_pepper_setting_is_optional_and_secret_safe() -> None:
    without_pepper = Settings(
        device_watch_env=Environment.TEST,
        database_url=DATABASE_URL,
    )
    configured = Settings(
        device_watch_env=Environment.TEST,
        database_url=DATABASE_URL,
        device_watch_bootstrap_hmac_pepper=HMAC_PEPPER,
    )

    assert without_pepper.device_watch_bootstrap_hmac_pepper is None
    assert isinstance(configured.device_watch_bootstrap_hmac_pepper, SecretStr)
    assert HMAC_PEPPER not in repr(configured)
    assert HMAC_PEPPER not in str(configured)


def test_bootstrap_pepper_loads_from_protected_uppercase_environment() -> None:
    with patch("os.environ", {
        "DEVICE_WATCH_ENV": "test",
        "DATABASE_URL": DATABASE_URL,
        "DEVICE_WATCH_BOOTSTRAP_HMAC_PEPPER": HMAC_PEPPER,
    }):
        settings = load_settings()

    pepper = settings.device_watch_bootstrap_hmac_pepper
    assert pepper is not None
    assert pepper.get_secret_value() == HMAC_PEPPER
    assert HMAC_PEPPER not in repr(settings)


def test_provisioning_expiry_matches_mysql_second_precision(
    connection: Connection, repository: _RepositoryDouble
) -> None:
    issued = provision_bootstrap(
        connection, HMAC_PEPPER, clock=lambda: NOW.replace(microsecond=987654)
    )

    assert issued.created_at == NOW
    assert issued.expires_at == NOW + timedelta(minutes=15)
    record = repository.records[issued.bootstrap_id]
    assert record.created_at == issued.created_at
    assert record.expires_at == issued.expires_at


@pytest.mark.parametrize("configured_value", ("p" * 31, "\u20ac" * 10))
def test_configured_bootstrap_pepper_requires_32_utf8_bytes(
    configured_value: str,
) -> None:
    with pytest.raises(ValidationError) as error:
        Settings(
            device_watch_env=Environment.TEST,
            database_url=DATABASE_URL,
            device_watch_bootstrap_hmac_pepper=configured_value,
        )

    assert configured_value not in str(error.value)


def test_provisioning_defaults_to_fifteen_minutes_and_stores_only_derivations(
    connection: Connection,
    repository: _RepositoryDouble,
) -> None:
    created = provision_bootstrap(
        connection,
        HMAC_PEPPER,
        operator_label="  night shift  ",
        clock=lambda: NOW,
    )

    wire_value = created.bootstrap_value.to_wire()
    stored = repository.records.get(created.bootstrap_id)
    assert DEFAULT_BOOTSTRAP_EXPIRY_MINUTES == 15
    assert created.created_at == NOW
    assert created.expires_at == NOW + timedelta(minutes=15)
    assert created.operator_label == "night shift"
    assert UUID(str(created.bootstrap_id)).version == 4
    assert BootstrapValue.parse(wire_value) == created.bootstrap_value
    assert wire_value not in repr(created)
    assert wire_value not in str(created)
    assert stored is not None
    assert stored.bootstrap_id == created.bootstrap_id
    assert stored.lookup_fingerprint == bootstrap_fingerprint(created.bootstrap_value)
    assert stored.digest_version == DIGEST_VERSION
    assert verify_bootstrap_digest(created.bootstrap_value, stored.digest, HMAC_PEPPER)
    assert stored.operator_label == "night shift"
    assert stored.created_at == NOW
    assert stored.expires_at == NOW + timedelta(minutes=15)
    assert stored.consumed_at is None
    assert stored.revoked_at is None
    assert wire_value not in repr(stored)


def test_provisioning_normalizes_utc_blank_labels_and_explicit_expiry(
    connection: Connection,
    repository: _RepositoryDouble,
) -> None:
    offset_now = datetime(2026, 9, 8, 17, 30, tzinfo=UTC_PLUS_0530)

    created = provision_bootstrap(
        connection,
        "\u20ac" * 11,
        expires_in_minutes=7,
        operator_label=" \t ",
        clock=lambda: offset_now,
    )

    assert created.created_at == NOW
    assert created.expires_at == NOW + timedelta(minutes=7)
    assert created.operator_label is None
    stored = repository.records.get(created.bootstrap_id)
    assert stored is not None
    assert stored.operator_label is None


@pytest.mark.parametrize("expires_in_minutes", (0, -1, True))
def test_provisioning_rejects_non_positive_or_non_integer_minute_counts(
    connection: Connection,
    repository: _RepositoryDouble,
    expires_in_minutes: object,
) -> None:
    with pytest.raises(BootstrapServiceError, match="Bootstrap operation failed"):
        provision_bootstrap(
            connection,
            HMAC_PEPPER,
            expires_in_minutes=expires_in_minutes,  # type: ignore[arg-type]
            clock=lambda: NOW,
        )

    assert repository.records == {}


def test_provisioning_rejects_an_overlong_label_before_writing(
    connection: Connection,
    repository: _RepositoryDouble,
) -> None:
    with pytest.raises(BootstrapServiceError, match="Bootstrap operation failed"):
        provision_bootstrap(
            connection,
            HMAC_PEPPER,
            operator_label="x" * 121,
            clock=lambda: NOW,
        )

    assert repository.records == {}


@pytest.mark.parametrize("configured_pepper", (None, "p" * 31, "\u20ac" * 10))
def test_provisioning_requires_a_configured_32_byte_pepper(
    connection: Connection,
    repository: _RepositoryDouble,
    configured_pepper: str | None,
) -> None:
    with pytest.raises(BootstrapServiceError, match="Bootstrap operation failed"):
        provision_bootstrap(
            connection,
            configured_pepper,
            clock=lambda: NOW,
        )

    assert repository.records == {}


def test_valid_bootstrap_is_consumed_once_at_server_utc(
    connection: Connection,
    repository: _RepositoryDouble,
) -> None:
    created = provision_bootstrap(
        connection,
        HMAC_PEPPER,
        clock=lambda: NOW,
    )
    consumed_at = datetime(2026, 9, 8, 17, 31, tzinfo=UTC_PLUS_0530)

    consumed_id = validate_and_consume_bootstrap(
        connection,
        created.bootstrap_value.to_wire(),
        HMAC_PEPPER,
        clock=lambda: consumed_at,
    )

    assert consumed_id == created.bootstrap_id
    stored = repository.records.get(created.bootstrap_id)
    assert stored is not None
    assert stored.consumed_at == NOW + timedelta(minutes=1)
    assert stored.revoked_at is None


def test_consumption_requests_a_row_lock_before_the_guarded_update(
    connection: Connection,
    repository: _RepositoryDouble,
) -> None:
    created = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)
    validate_and_consume_bootstrap(
        connection,
        created.bootstrap_value.to_wire(),
        HMAC_PEPPER,
        clock=lambda: NOW + timedelta(seconds=1),
    )

    assert repository.calls == [
        ("fingerprint", bootstrap_fingerprint(created.bootstrap_value), True),
        ("consume", created.bootstrap_id, NOW + timedelta(seconds=1)),
    ]


def test_all_invalid_bootstrap_states_have_one_generic_failure(
    connection: Connection,
    repository: _RepositoryDouble,
) -> None:
    available = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)
    expired = provision_bootstrap(
        connection,
        HMAC_PEPPER,
        expires_in_minutes=1,
        clock=lambda: NOW,
    )
    revoked = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)
    consumed = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)
    future_digest = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)
    revoke_bootstrap(
        connection,
        revoked.bootstrap_id,
        clock=lambda: NOW + timedelta(seconds=1),
    )
    validate_and_consume_bootstrap(
        connection,
        consumed.bootstrap_value.to_wire(),
        HMAC_PEPPER,
        clock=lambda: NOW + timedelta(seconds=1),
    )
    repository.records[future_digest.bootstrap_id] = replace(
        repository.records[future_digest.bootstrap_id], digest_version="hmac-sha256-v2"
    )

    attempts = (
        ("not-a-bootstrap", HMAC_PEPPER, NOW + timedelta(seconds=2)),
        (UNKNOWN_WIRE_VALUE, HMAC_PEPPER, NOW + timedelta(seconds=2)),
        (
            available.bootstrap_value.to_wire(),
            OTHER_HMAC_PEPPER,
            NOW + timedelta(seconds=2),
        ),
        (
            expired.bootstrap_value.to_wire(),
            HMAC_PEPPER,
            NOW + timedelta(minutes=1),
        ),
        (
            revoked.bootstrap_value.to_wire(),
            HMAC_PEPPER,
            NOW + timedelta(seconds=2),
        ),
        (
            consumed.bootstrap_value.to_wire(),
            HMAC_PEPPER,
            NOW + timedelta(seconds=2),
        ),
        (
            future_digest.bootstrap_value.to_wire(),
            HMAC_PEPPER,
            NOW + timedelta(seconds=2),
        ),
    )
    messages: set[str] = set()
    for wire_value, configured_pepper, checked_at in attempts:
        with pytest.raises(BootstrapServiceError) as error:
            validate_and_consume_bootstrap(
                connection,
                wire_value,
                configured_pepper,
                clock=lambda checked_at=checked_at: checked_at,
            )
        messages.add(str(error.value))
        assert wire_value not in str(error.value)

    assert messages == {"Bootstrap operation failed"}
    expired_record = repository.records.get(expired.bootstrap_id)
    assert expired_record is not None
    assert expired_record.consumed_at is None


@pytest.mark.parametrize("configured_pepper", (None, "p" * 31, "\u20ac" * 10))
def test_plaintext_verification_requires_a_configured_32_byte_pepper(
    connection: Connection,
    repository: _RepositoryDouble,
    configured_pepper: str | None,
) -> None:
    created = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)

    with pytest.raises(BootstrapServiceError, match="Bootstrap operation failed"):
        validate_and_consume_bootstrap(
            connection,
            created.bootstrap_value.to_wire(),
            configured_pepper,
            clock=lambda: NOW + timedelta(seconds=1),
        )

    stored = repository.records.get(created.bootstrap_id)
    assert stored is not None
    assert stored.consumed_at is None


def test_revocation_transitions_only_an_available_record(
    connection: Connection,
    repository: _RepositoryDouble,
) -> None:
    created = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)

    revoked_id = revoke_bootstrap(
        connection,
        created.bootstrap_id,
        clock=lambda: NOW + timedelta(minutes=1),
    )

    assert revoked_id == created.bootstrap_id
    stored = repository.records.get(created.bootstrap_id)
    assert stored is not None
    assert stored.consumed_at is None
    assert stored.revoked_at == NOW + timedelta(minutes=1)
    with pytest.raises(BootstrapServiceError, match="Bootstrap operation failed"):
        revoke_bootstrap(
            connection,
            created.bootstrap_id,
            clock=lambda: NOW + timedelta(minutes=2),
        )


def test_revocation_requests_a_row_lock_before_the_guarded_update(
    connection: Connection,
    repository: _RepositoryDouble,
) -> None:
    created = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)
    revoke_bootstrap(
        connection,
        created.bootstrap_id,
        clock=lambda: NOW + timedelta(seconds=1),
    )

    assert repository.calls == [
        ("id", created.bootstrap_id, True),
        ("revoke", created.bootstrap_id, NOW + timedelta(seconds=1)),
    ]


def test_revocation_rejects_unknown_consumed_and_expired_records_generically(
    connection: Connection,
    repository: _RepositoryDouble,
) -> None:
    consumed = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)
    expired = provision_bootstrap(
        connection,
        HMAC_PEPPER,
        expires_in_minutes=1,
        clock=lambda: NOW,
    )
    validate_and_consume_bootstrap(
        connection,
        consumed.bootstrap_value.to_wire(),
        HMAC_PEPPER,
        clock=lambda: NOW + timedelta(seconds=1),
    )

    messages: set[str] = set()
    for bootstrap_id, checked_at in (
        (UUID("7eed98e3-87f1-4ba9-8aa9-c96dd13b70ea"), NOW),
        (consumed.bootstrap_id, NOW + timedelta(seconds=2)),
        (expired.bootstrap_id, NOW + timedelta(minutes=1)),
    ):
        with pytest.raises(BootstrapServiceError) as error:
            revoke_bootstrap(
                connection,
                bootstrap_id,
                clock=lambda checked_at=checked_at: checked_at,
            )
        messages.add(str(error.value))

    assert messages == {"Bootstrap operation failed"}
    expired_record = repository.records.get(expired.bootstrap_id)
    assert expired_record is not None
    assert expired_record.revoked_at is None


def test_service_operations_leave_transactions_owned_by_the_caller(
    connection: Connection,
    repository: _RepositoryDouble,
) -> None:
    created = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)
    validate_and_consume_bootstrap(
        connection,
        created.bootstrap_value.to_wire(),
        HMAC_PEPPER,
        clock=lambda: NOW + timedelta(seconds=1),
    )
    revocable = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)
    revoke_bootstrap(
        connection,
        revocable.bootstrap_id,
        clock=lambda: NOW + timedelta(seconds=2),
    )
    assert repository.records[created.bootstrap_id].consumed_at is not None
    assert repository.records[revocable.bootstrap_id].revoked_at is not None
    # The connection fixture rejects transaction ownership by every service call.
