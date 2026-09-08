"""Add secret-safe enrollment bootstrap storage.

Revision ID: 20260908_0003
Revises: 20260908_0002
Create Date: 2026-09-08 00:03:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260908_0003"
down_revision = "20260908_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the server-owned one-time bootstrap store."""
    op.create_table(
        "enrollment_bootstraps",
        sa.Column("bootstrap_id", sa.String(length=36), nullable=False),
        sa.Column("lookup_fingerprint", sa.BINARY(length=32), nullable=False),
        sa.Column("digest_version", sa.String(length=32), nullable=False),
        sa.Column("digest", sa.BINARY(length=32), nullable=False),
        sa.Column("operator_label", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_enrollment_bootstraps_expires_after_created",
        ),
        sa.CheckConstraint(
            "consumed_at IS NULL OR revoked_at IS NULL",
            name="ck_enrollment_bootstraps_terminal_exclusive",
        ),
        sa.CheckConstraint(
            "consumed_at IS NULL OR consumed_at >= created_at",
            name="ck_enrollment_bootstraps_consumed_not_before_created",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_enrollment_bootstraps_revoked_not_before_created",
        ),
        sa.PrimaryKeyConstraint("bootstrap_id", name="pk_enrollment_bootstraps"),
        sa.UniqueConstraint(
            "lookup_fingerprint",
            name="uq_enrollment_bootstraps_lookup_fingerprint",
        ),
    )


def downgrade() -> None:
    """Remove the one-time bootstrap store."""
    op.drop_table("enrollment_bootstraps")
