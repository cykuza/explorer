"""Add mweb_blocks and txs.is_hogex.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mweb_blocks",
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("hash", sa.Text(), nullable=False),
        sa.Column("kernel_offset", sa.Text(), nullable=True),
        sa.Column("stealth_offset", sa.Text(), nullable=True),
        sa.Column("num_kernels", sa.Integer(), nullable=False),
        sa.Column("num_txos", sa.Integer(), nullable=False),
        sa.Column("kernel_root", sa.Text(), nullable=True),
        sa.Column("output_root", sa.Text(), nullable=True),
        sa.Column("leaf_root", sa.Text(), nullable=True),
        sa.Column("mweb_amount", sa.Numeric(), nullable=False),
        sa.Column("pegin", sa.Numeric(), nullable=False),
        sa.Column("pegout", sa.Numeric(), nullable=False),
        sa.Column("kernel_fees", sa.Numeric(), nullable=False),
        sa.Column("hogex_txid", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["height"], ["blocks.height"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("height"),
    )
    op.add_column(
        "txs",
        sa.Column(
            "is_hogex",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("txs", "is_hogex")
    op.drop_table("mweb_blocks")
