"""Add hash-only device credential persistence for atomic enrollment.

Revision ID: 20260913_0004
Revises: 20260908_0003
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260913_0004"
down_revision = "20260908_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_credentials",
        sa.Column("key_id", sa.String(32), nullable=False),
        sa.Column("device_id", sa.String(36), nullable=False),
        sa.Column("secret_hash", sa.String(97), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("replaced_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("key_id", name="pk_device_credentials"),
        sa.ForeignKeyConstraint(
            ["device_id"], ["devices.device_id"],
            name="fk_device_credentials_device_id_devices", ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "last_used_at IS NULL OR last_used_at >= created_at",
            name="ck_device_credentials_last_used_not_before_created",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_device_credentials_revoked_not_before_created",
        ),
        sa.CheckConstraint(
            "replaced_at IS NULL OR (revoked_at IS NOT NULL AND replaced_at = revoked_at)",
            name="ck_device_credentials_replaced_requires_revocation",
        ),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_device_credentials_device_id", "device_credentials", ["device_id"])


def downgrade() -> None:
    op.drop_table("device_credentials")
