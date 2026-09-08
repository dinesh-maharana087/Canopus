"""Schema-empty baseline revision.

Revision ID: 20260831_0001
Revises: None
Create Date: 2026-08-31 00:01:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "20260831_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the schema-empty baseline."""

    pass


def downgrade() -> None:
    """Return to the empty base state."""

    pass
