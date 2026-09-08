from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import create_engine, event, update
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import Connection
from sqlalchemy.sql.elements import ClauseElement

from device_watch_server.core.config import Environment, Settings
from device_watch_server.enrollment.bootstrap import (
    DIGEST_VERSION,
    BootstrapValue,
    bootstrap_fingerprint,
    verify_bootstrap_digest,
)
from device_watch_server.enrollment.repository import (
    bootstrap_table,
    lookup_bootstrap_by_id,
)
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
    engine = create_engine("sqlite+pysqlite:///:memory:")
    bootstrap_table.create(engine)
    with engine.connect() as active_connection:
        yield active_connection
    engine.dispose()


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
) -> None:
    created = provision_bootstrap(
        connection,
        HMAC_PEPPER,
        operator_label="  night shift  ",
        clock=lambda: NOW,
    )

    wire_value = created.bootstrap_value.to_wire()
    stored = lookup_bootstrap_by_id(connection, created.bootstrap_id)
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
    stored = lookup_bootstrap_by_id(connection, created.bootstrap_id)
    assert stored is not None
    assert stored.operator_label is None


@pytest.mark.parametrize("expires_in_minutes", (0, -1, True))
def test_provisioning_rejects_non_positive_or_non_integer_minute_counts(
    connection: Connection,
    expires_in_minutes: object,
) -> None:
    with pytest.raises(BootstrapServiceError, match="Bootstrap operation failed"):
        provision_bootstrap(
            connection,
            HMAC_PEPPER,
            expires_in_minutes=expires_in_minutes,  # type: ignore[arg-type]
            clock=lambda: NOW,
        )

    assert connection.execute(bootstrap_table.select()).all() == []


def test_provisioning_rejects_an_overlong_label_before_writing(
    connection: Connection,
) -> None:
    with pytest.raises(BootstrapServiceError, match="Bootstrap operation failed"):
        provision_bootstrap(
            connection,
            HMAC_PEPPER,
            operator_label="x" * 121,
            clock=lambda: NOW,
        )

    assert connection.execute(bootstrap_table.select()).all() == []


@pytest.mark.parametrize("configured_pepper", (None, "p" * 31, "\u20ac" * 10))
def test_provisioning_requires_a_configured_32_byte_pepper(
    connection: Connection,
    configured_pepper: str | None,
) -> None:
    with pytest.raises(BootstrapServiceError, match="Bootstrap operation failed"):
        provision_bootstrap(
            connection,
            configured_pepper,
            clock=lambda: NOW,
        )

    assert connection.execute(bootstrap_table.select()).all() == []


def test_valid_bootstrap_is_consumed_once_at_server_utc(
    connection: Connection,
) -> None:
    created = provision_bootstrap(
        connection,
        HMAC_PEPPER,
        clock=lambda: NOW,
    )
    connection.commit()
    consumed_at = datetime(2026, 9, 8, 17, 31, tzinfo=UTC_PLUS_0530)

    consumed_id = validate_and_consume_bootstrap(
        connection,
        created.bootstrap_value.to_wire(),
        HMAC_PEPPER,
        clock=lambda: consumed_at,
    )

    assert consumed_id == created.bootstrap_id
    stored = lookup_bootstrap_by_id(connection, created.bootstrap_id)
    assert stored is not None
    assert stored.consumed_at == NOW + timedelta(minutes=1)
    assert stored.revoked_at is None


def test_consumption_requests_a_row_lock_before_the_guarded_update(
    connection: Connection,
) -> None:
    created = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)
    connection.commit()
    statements: list[ClauseElement] = []

    def capture_statement(*args: object) -> None:
        statements.append(cast(ClauseElement, args[1]))

    event.listen(connection, "before_execute", capture_statement)
    try:
        validate_and_consume_bootstrap(
            connection,
            created.bootstrap_value.to_wire(),
            HMAC_PEPPER,
            clock=lambda: NOW + timedelta(seconds=1),
        )
    finally:
        event.remove(connection, "before_execute", capture_statement)

    compiled = [
        str(statement.compile(dialect=mysql.dialect())).lower()
        for statement in statements
    ]
    assert any(
        "select" in statement
        and "lookup_fingerprint" in statement
        and "for update" in statement
        for statement in compiled
    )


def test_all_invalid_bootstrap_states_have_one_generic_failure(
    connection: Connection,
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
    connection.execute(
        update(bootstrap_table)
        .where(bootstrap_table.c.bootstrap_id == str(future_digest.bootstrap_id))
        .values(digest_version="hmac-sha256-v2")
    )
    connection.commit()

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
    expired_record = lookup_bootstrap_by_id(connection, expired.bootstrap_id)
    assert expired_record is not None
    assert expired_record.consumed_at is None


@pytest.mark.parametrize("configured_pepper", (None, "p" * 31, "\u20ac" * 10))
def test_plaintext_verification_requires_a_configured_32_byte_pepper(
    connection: Connection,
    configured_pepper: str | None,
) -> None:
    created = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)
    connection.commit()

    with pytest.raises(BootstrapServiceError, match="Bootstrap operation failed"):
        validate_and_consume_bootstrap(
            connection,
            created.bootstrap_value.to_wire(),
            configured_pepper,
            clock=lambda: NOW + timedelta(seconds=1),
        )

    stored = lookup_bootstrap_by_id(connection, created.bootstrap_id)
    assert stored is not None
    assert stored.consumed_at is None


def test_revocation_transitions_only_an_available_record(
    connection: Connection,
) -> None:
    created = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)

    revoked_id = revoke_bootstrap(
        connection,
        created.bootstrap_id,
        clock=lambda: NOW + timedelta(minutes=1),
    )

    assert revoked_id == created.bootstrap_id
    stored = lookup_bootstrap_by_id(connection, created.bootstrap_id)
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
) -> None:
    created = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)
    connection.commit()
    statements: list[ClauseElement] = []

    def capture_statement(*args: object) -> None:
        statements.append(cast(ClauseElement, args[1]))

    event.listen(connection, "before_execute", capture_statement)
    try:
        revoke_bootstrap(
            connection,
            created.bootstrap_id,
            clock=lambda: NOW + timedelta(seconds=1),
        )
    finally:
        event.remove(connection, "before_execute", capture_statement)

    compiled = [
        str(statement.compile(dialect=mysql.dialect())).lower()
        for statement in statements
    ]
    assert any(
        "select" in statement
        and "bootstrap_id" in statement
        and "for update" in statement
        for statement in compiled
    )


def test_revocation_rejects_unknown_consumed_and_expired_records_generically(
    connection: Connection,
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
    connection.commit()

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
    expired_record = lookup_bootstrap_by_id(connection, expired.bootstrap_id)
    assert expired_record is not None
    assert expired_record.revoked_at is None


def test_service_operations_leave_transactions_owned_by_the_caller(
    connection: Connection,
) -> None:
    create_transaction = connection.begin()
    created = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)
    assert create_transaction.is_active
    create_transaction.rollback()
    assert lookup_bootstrap_by_id(connection, created.bootstrap_id) is None
    connection.commit()

    created = provision_bootstrap(connection, HMAC_PEPPER, clock=lambda: NOW)
    connection.commit()
    consume_transaction = connection.begin()
    validate_and_consume_bootstrap(
        connection,
        created.bootstrap_value.to_wire(),
        HMAC_PEPPER,
        clock=lambda: NOW + timedelta(seconds=1),
    )
    assert consume_transaction.is_active
    consume_transaction.rollback()
    stored = lookup_bootstrap_by_id(connection, created.bootstrap_id)
    assert stored is not None
    assert stored.consumed_at is None
    connection.commit()

    revoke_transaction = connection.begin()
    revoke_bootstrap(
        connection,
        created.bootstrap_id,
        clock=lambda: NOW + timedelta(seconds=2),
    )
    assert revoke_transaction.is_active
    revoke_transaction.rollback()
    stored = lookup_bootstrap_by_id(connection, created.bootstrap_id)
    assert stored is not None
    assert stored.revoked_at is None
