"""Insert-only device and credential persistence for the enrollment transaction."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, MetaData, String, Table
from sqlalchemy.engine import Connection

from device_watch_server.auth.credentials import CredentialRecord
from device_watch_server.domain.contracts import DeviceIdentity

_metadata = MetaData()
devices_table = Table(
    "devices",
    _metadata,
    Column("device_id", String(36), primary_key=True),
    Column("display_name", String(120), nullable=False),
    Column("created_at", DateTime(), nullable=False),
    Column("lifecycle", String(16), nullable=False),
)
credentials_table = Table(
    "device_credentials",
    _metadata,
    Column("key_id", String(32), primary_key=True),
    Column("device_id", String(36), ForeignKey("devices.device_id"), nullable=False),
    Column("secret_hash", String(97), nullable=False),
    Column("created_at", DateTime(), nullable=False),
    Column("last_used_at", DateTime(), nullable=True),
    Column("revoked_at", DateTime(), nullable=True),
    Column("replaced_at", DateTime(), nullable=True),
)


def _mysql_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Invalid persistence timestamp")
    return value.astimezone(UTC).replace(tzinfo=None, microsecond=0)


def insert_device(connection: Connection, device: DeviceIdentity) -> None:
    """Persist only the identity columns using the caller's transaction."""
    connection.execute(
        devices_table.insert().values(
            device_id=str(device.device_id),
            display_name=device.display_name,
            created_at=_mysql_time(device.created_at),
            lifecycle=device.lifecycle.value,
        )
    )


def insert_credential(
    connection: Connection,
    device_id: UUID,
    credential: CredentialRecord,
) -> None:
    """Persist only the hash representation, never the issued secret carrier."""
    connection.execute(
        credentials_table.insert().values(
            key_id=credential.key_id,
            device_id=str(device_id),
            secret_hash=credential.secret_hash,
            created_at=_mysql_time(credential.created_at),
            last_used_at=None,
            revoked_at=None
            if credential.revoked_at is None
            else _mysql_time(credential.revoked_at),
            replaced_at=None
            if credential.replaced_at is None
            else _mysql_time(credential.replaced_at),
        )
    )
