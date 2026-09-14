"""Current-state column projection of devices; Alembic owns the physical schema.

The existing identity-only enrollment projection remains usable at revision 0004.
This separate Core metadata describes only the 0005 connectivity boundary, not a
second table to create. Do not call create_all() on projection metadata.

Store server receipt times as naive UTC with microsecond precision. Only the
latest submission ID per device is retained, until replaced; there is no history.
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, Index, MetaData, String, Table
from sqlalchemy.dialects import mysql

device_connectivity_table = Table(
    "devices",
    MetaData(),
    Column("device_id", String(36), primary_key=True),
    Column("last_seen_at", mysql.DATETIME(fsp=6), nullable=True),
    Column("last_heartbeat_submission_id", String(36), nullable=True),
    Column("last_agent_version", String(64), nullable=True),
    CheckConstraint(
        "last_heartbeat_submission_id IS NULL OR last_seen_at IS NOT NULL",
        name="ck_devices_submission_requires_last_seen",
    ),
    Index("ix_devices_last_seen_at", "last_seen_at"),
)
