"""Add server-owned device identity storage.

Revision ID: 20260908_0002
Revises: 20260831_0001
Create Date: 2026-09-08 00:02:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260908_0002"
down_revision = "20260831_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the identity-only device table."""

    op.create_table(
        "devices",
        sa.Column("device_id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "lifecycle",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.CheckConstraint(
            "lifecycle IN ('active', 'revoked')",
            name="ck_devices_lifecycle",
        ),
        sa.PrimaryKeyConstraint("device_id", name="pk_devices"),
    )


def downgrade() -> None:
    """Remove the identity-only device table."""

    op.drop_table("devices")
