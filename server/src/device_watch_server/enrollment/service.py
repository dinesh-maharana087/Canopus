"""Transaction-composable bootstrap provisioning and lifecycle service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.engine import Connection

from device_watch_server.domain.contracts import BootstrapState
from device_watch_server.enrollment.bootstrap import (
    DIGEST_VERSION,
    BootstrapLifecycle,
    BootstrapValue,
    bootstrap_digest,
    bootstrap_fingerprint,
    generate_bootstrap_value,
    verify_bootstrap_digest,
)
from device_watch_server.enrollment.repository import (
    BootstrapRecord,
    insert_bootstrap,
    lookup_bootstrap_by_fingerprint,
    lookup_bootstrap_by_id,
)
from device_watch_server.enrollment.repository import (
    consume_bootstrap as mark_bootstrap_consumed,
)
from device_watch_server.enrollment.repository import (
    revoke_bootstrap as mark_bootstrap_revoked,
)

DEFAULT_BOOTSTRAP_EXPIRY_MINUTES = 15
MAX_OPERATOR_LABEL_LENGTH = 120
GENERIC_BOOTSTRAP_FAILURE = "Bootstrap operation failed"
_MINIMUM_PEPPER_BYTES = 32

Clock = Callable[[], datetime]


class BootstrapServiceError(ValueError):
    """A deliberately generic bootstrap failure safe for boundary mapping."""

    def __init__(self) -> None:
        super().__init__(GENERIC_BOOTSTRAP_FAILURE)


@dataclass(frozen=True, repr=False)
class ProvisionedBootstrap:
    """One-time provisioning result with masked default representations."""

    bootstrap_id: UUID
    bootstrap_value: BootstrapValue
    operator_label: str | None
    created_at: datetime
    expires_at: datetime

    def __repr__(self) -> str:
        return (
            "ProvisionedBootstrap("
            f"bootstrap_id={self.bootstrap_id!r}, "
            f"operator_label={self.operator_label!r}, "
            f"created_at={self.created_at!r}, "
            f"expires_at={self.expires_at!r}, "
            "bootstrap_value=<redacted>)"
        )

    __str__ = __repr__


def _failure() -> BootstrapServiceError:
    return BootstrapServiceError()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _server_utc(clock: Clock) -> datetime:
    current = clock()
    if not isinstance(current, datetime):
        raise _failure()
    if current.tzinfo is None or current.utcoffset() is None:
        raise _failure()
    # MySQL DATETIME in the approved bootstrap migration stores whole seconds.
    return current.astimezone(UTC).replace(microsecond=0)


def _require_hmac_pepper(configured_pepper: str | None) -> str:
    if not isinstance(configured_pepper, str):
        raise _failure()
    try:
        pepper_bytes = configured_pepper.encode("utf-8")
    except UnicodeEncodeError:
        raise _failure() from None
    if len(pepper_bytes) < _MINIMUM_PEPPER_BYTES:
        raise _failure()
    return configured_pepper


def _normalize_operator_label(operator_label: str | None) -> str | None:
    if operator_label is None:
        return None
    if not isinstance(operator_label, str):
        raise _failure()
    normalized = operator_label.strip()
    if not normalized:
        return None
    if len(normalized) > MAX_OPERATOR_LABEL_LENGTH:
        raise _failure()
    return normalized


def _require_expiry_minutes(expires_in_minutes: int) -> int:
    if isinstance(expires_in_minutes, bool) or not isinstance(expires_in_minutes, int):
        raise _failure()
    if expires_in_minutes <= 0:
        raise _failure()
    return expires_in_minutes


def _lifecycle(record: BootstrapRecord) -> BootstrapLifecycle:
    try:
        return BootstrapLifecycle(
            created_at=record.created_at,
            expires_at=record.expires_at,
            consumed_at=record.consumed_at,
            revoked_at=record.revoked_at,
        )
    except ValueError:
        raise _failure() from None


def provision_bootstrap(
    connection: Connection,
    configured_pepper: str | None,
    *,
    expires_in_minutes: int = DEFAULT_BOOTSTRAP_EXPIRY_MINUTES,
    operator_label: str | None = None,
    clock: Clock = _utc_now,
) -> ProvisionedBootstrap:
    """Create and insert one bootstrap without committing its transaction."""

    hmac_pepper = _require_hmac_pepper(configured_pepper)
    lifetime_minutes = _require_expiry_minutes(expires_in_minutes)
    normalized_label = _normalize_operator_label(operator_label)
    created_at = _server_utc(clock)
    try:
        expires_at = created_at + timedelta(minutes=lifetime_minutes)
    except OverflowError:
        raise _failure() from None
    bootstrap_value = generate_bootstrap_value()
    bootstrap_id = uuid4()
    record = BootstrapRecord(
        bootstrap_id=bootstrap_id,
        lookup_fingerprint=bootstrap_fingerprint(bootstrap_value),
        digest_version=DIGEST_VERSION,
        digest=bootstrap_digest(bootstrap_value, hmac_pepper),
        operator_label=normalized_label,
        created_at=created_at,
        expires_at=expires_at,
        consumed_at=None,
        revoked_at=None,
    )
    insert_bootstrap(connection, record)
    return ProvisionedBootstrap(
        bootstrap_id=bootstrap_id,
        bootstrap_value=bootstrap_value,
        operator_label=normalized_label,
        created_at=created_at,
        expires_at=expires_at,
    )


def validate_and_consume_bootstrap(
    connection: Connection,
    wire_value: str,
    configured_pepper: str | None,
    *,
    clock: Clock = _utc_now,
) -> UUID:
    """Lock, validate, and consume one bootstrap without committing."""

    hmac_pepper = _require_hmac_pepper(configured_pepper)
    try:
        bootstrap_value = BootstrapValue.parse(wire_value)
    except (TypeError, ValueError):
        raise _failure() from None

    fingerprint = bootstrap_fingerprint(bootstrap_value)
    record = lookup_bootstrap_by_fingerprint(
        connection,
        fingerprint,
        for_update=True,
    )
    stored_digest = bytes(32) if record is None else record.digest
    digest_matches = verify_bootstrap_digest(
        bootstrap_value,
        stored_digest,
        hmac_pepper,
    )
    if (
        record is None
        or record.digest_version != DIGEST_VERSION
        or not digest_matches
    ):
        raise _failure()

    consumed_at = _server_utc(clock)
    if _lifecycle(record).state_at(consumed_at) is not BootstrapState.AVAILABLE:
        raise _failure()
    if not mark_bootstrap_consumed(connection, record.bootstrap_id, consumed_at):
        raise _failure()
    return record.bootstrap_id


def revoke_bootstrap(
    connection: Connection,
    bootstrap_id: UUID,
    *,
    clock: Clock = _utc_now,
) -> UUID:
    """Lock and revoke one available bootstrap without committing."""

    record = lookup_bootstrap_by_id(connection, bootstrap_id, for_update=True)
    if record is None:
        raise _failure()
    revoked_at = _server_utc(clock)
    if _lifecycle(record).state_at(revoked_at) is not BootstrapState.AVAILABLE:
        raise _failure()
    if not mark_bootstrap_revoked(connection, record.bootstrap_id, revoked_at):
        raise _failure()
    return record.bootstrap_id


__all__ = [
    "DEFAULT_BOOTSTRAP_EXPIRY_MINUTES",
    "GENERIC_BOOTSTRAP_FAILURE",
    "BootstrapServiceError",
    "ProvisionedBootstrap",
    "provision_bootstrap",
    "revoke_bootstrap",
    "validate_and_consume_bootstrap",
]
