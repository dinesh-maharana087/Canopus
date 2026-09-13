"""Atomic enrollment service, independent of HTTP request/response contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from device_watch_server.auth.credentials import CredentialValue, issue_credential
from device_watch_server.domain.contracts import DeviceIdentity
from device_watch_server.enrollment.persistence import insert_credential, insert_device
from device_watch_server.enrollment.service import validate_and_consume_bootstrap

Clock = Callable[[], datetime]


class EnrollmentError(ValueError):
    """One sanitized failure for invalid state, issuance, storage, or commit errors."""

    def __init__(self) -> None:
        super().__init__("Enrollment failed")


@dataclass(frozen=True, repr=False)
class EnrollmentResult:
    """Transient success delivery with no bootstrap or credential hash attached."""

    device: DeviceIdentity
    credential: CredentialValue

    def __repr__(self) -> str:
        return "EnrollmentResult(<redacted>)"

    __str__ = __repr__


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _creation_time(clock: Clock) -> datetime:
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise EnrollmentError()
    return value.astimezone(UTC).replace(microsecond=0)


def enroll_device(
    engine: Engine, bootstrap_secret: str, configured_pepper: str | None,
    *, display_name: str, clock: Clock = _utc_now,
) -> EnrollmentResult:
    """Consume bootstrap and insert identity/hash on one connection, then deliver.

    The caller supplies the centrally configured MySQL engine. Participating
    tables must use InnoDB. There is no retry or credential replay: an uncertain
    commit outcome requires operator recovery, not automatic re-enrollment.
    """
    try:
        with engine.begin() as connection:
            # Pass the live clock: bootstrap validation samples it AFTER row locking.
            validate_and_consume_bootstrap(
                connection, bootstrap_secret, configured_pepper, clock=clock,
            )
            created_at = _creation_time(clock)
            device = DeviceIdentity(
                device_id=uuid4(), display_name=display_name, created_at=created_at,
            )
            insert_device(connection, device)
            issued = issue_credential(clock=lambda: created_at)
            insert_credential(connection, device.device_id, issued.record)
            result = EnrollmentResult(device=device, credential=issued.value)
        # A commit exception exits through the sanitized failure below, never here.
        return result
    except (SQLAlchemyError, ValueError, OSError, RuntimeError):
        raise EnrollmentError() from None
