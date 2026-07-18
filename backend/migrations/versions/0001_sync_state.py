"""Create sync_state table.

Revision ID: 0001
Revises:
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sync_state",
        sa.Column("network", sa.Text(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("tip_hash", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("network"),
    )


def downgrade() -> None:
    op.drop_table("sync_state")
