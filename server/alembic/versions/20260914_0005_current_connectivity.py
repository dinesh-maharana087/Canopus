"""Add only current connectivity inputs to each device.

Revision ID: 20260914_0005
Revises: 20260913_0004

One device row retains only its latest submission ID, until replaced; no TTL or
history. Receipt times are server-owned UTC stored without a timezone, retaining
microseconds. No default or ON UPDATE may refresh last-seen implicitly.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision = "20260914_0005"
down_revision = "20260913_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "devices", sa.Column("last_seen_at", mysql.DATETIME(fsp=6), nullable=True)
    )
    op.add_column(
        "devices",
        sa.Column("last_heartbeat_submission_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "devices", sa.Column("last_agent_version", sa.String(64), nullable=True)
    )
    op.create_check_constraint(
        op.f("ck_devices_submission_requires_last_seen"),
        "devices",
        "last_heartbeat_submission_id IS NULL OR last_seen_at IS NOT NULL",
    )
    op.create_index("ix_devices_last_seen_at", "devices", ["last_seen_at"])


def downgrade() -> None:
    """Discard current connectivity values while preserving prior device identity."""
    op.drop_index("ix_devices_last_seen_at", table_name="devices")
    op.drop_constraint(
        op.f("ck_devices_submission_requires_last_seen"), "devices", type_="check"
    )
    op.drop_column("devices", "last_agent_version")
    op.drop_column("devices", "last_heartbeat_submission_id")
    op.drop_column("devices", "last_seen_at")
