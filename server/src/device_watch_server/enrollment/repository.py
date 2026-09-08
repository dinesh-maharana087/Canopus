"""SQLAlchemy Core persistence operations for enrollment bootstraps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import BINARY, Column, DateTime, MetaData, String, Table, select
from sqlalchemy.engine import Connection, RowMapping

_metadata = MetaData()

bootstrap_table = Table(
    "enrollment_bootstraps",
    _metadata,
    Column("bootstrap_id", String(length=36), primary_key=True),
    Column("lookup_fingerprint", BINARY(length=32), unique=True, nullable=False),
    Column("digest_version", String(length=32), nullable=False),
    Column("digest", BINARY(length=32), nullable=False),
    Column("operator_label", String(length=120), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("consumed_at", DateTime(timezone=True), nullable=True),
    Column("revoked_at", DateTime(timezone=True), nullable=True),
)


@dataclass(frozen=True)
class BootstrapRecord:
    """Stored bootstrap material, excluding any plaintext bootstrap value."""

    bootstrap_id: UUID
    lookup_fingerprint: bytes
    digest_version: str
    digest: bytes
    operator_label: str | None
    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None
    revoked_at: datetime | None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _record_from_row(row: RowMapping) -> BootstrapRecord:
    consumed_at = cast(datetime | None, row["consumed_at"])
    revoked_at = cast(datetime | None, row["revoked_at"])
    return BootstrapRecord(
        bootstrap_id=UUID(cast(str, row["bootstrap_id"])),
        lookup_fingerprint=cast(bytes, row["lookup_fingerprint"]),
        digest_version=cast(str, row["digest_version"]),
        digest=cast(bytes, row["digest"]),
        operator_label=cast(str | None, row["operator_label"]),
        created_at=_as_utc(cast(datetime, row["created_at"])),
        expires_at=_as_utc(cast(datetime, row["expires_at"])),
        consumed_at=None if consumed_at is None else _as_utc(consumed_at),
        revoked_at=None if revoked_at is None else _as_utc(revoked_at),
    )


def insert_bootstrap(connection: Connection, record: BootstrapRecord) -> None:
    """Insert one bootstrap using the caller-owned transaction."""
    connection.execute(
        bootstrap_table.insert().values(
            bootstrap_id=str(record.bootstrap_id),
            lookup_fingerprint=record.lookup_fingerprint,
            digest_version=record.digest_version,
            digest=record.digest,
            operator_label=record.operator_label,
            created_at=record.created_at,
            expires_at=record.expires_at,
            consumed_at=record.consumed_at,
            revoked_at=record.revoked_at,
        )
    )


def lookup_bootstrap_by_fingerprint(
    connection: Connection, fingerprint: bytes, *, for_update: bool = False
) -> BootstrapRecord | None:
    """Look up stored material by non-secret fingerprint, optionally locking it."""
    statement = select(bootstrap_table).where(
        bootstrap_table.c.lookup_fingerprint == fingerprint
    )
    if for_update:
        statement = statement.with_for_update()
    row = connection.execute(statement).mappings().one_or_none()
    return None if row is None else _record_from_row(row)


def lookup_bootstrap_by_id(
    connection: Connection, bootstrap_id: UUID
) -> BootstrapRecord | None:
    """Look up a bootstrap by its non-secret operator-visible identifier."""
    row = (
        connection.execute(
            select(bootstrap_table).where(
                bootstrap_table.c.bootstrap_id == str(bootstrap_id)
            )
        )
        .mappings()
        .one_or_none()
    )
    return None if row is None else _record_from_row(row)


def consume_bootstrap(
    connection: Connection, bootstrap_id: UUID, consumed_at: datetime
) -> bool:
    """Set consumption once, preserving any prior terminal transition."""
    result = connection.execute(
        bootstrap_table.update()
        .where(
            bootstrap_table.c.bootstrap_id == str(bootstrap_id),
            bootstrap_table.c.consumed_at.is_(None),
            bootstrap_table.c.revoked_at.is_(None),
        )
        .values(consumed_at=consumed_at)
    )
    return result.rowcount == 1


def revoke_bootstrap(
    connection: Connection, bootstrap_id: UUID, revoked_at: datetime
) -> bool:
    """Set revocation once, preserving any prior terminal transition."""
    result = connection.execute(
        bootstrap_table.update()
        .where(
            bootstrap_table.c.bootstrap_id == str(bootstrap_id),
            bootstrap_table.c.consumed_at.is_(None),
            bootstrap_table.c.revoked_at.is_(None),
        )
        .values(revoked_at=revoked_at)
    )
    return result.rowcount == 1


__all__ = [
    "BootstrapRecord",
    "bootstrap_table",
    "consume_bootstrap",
    "insert_bootstrap",
    "lookup_bootstrap_by_fingerprint",
    "lookup_bootstrap_by_id",
    "revoke_bootstrap",
]
