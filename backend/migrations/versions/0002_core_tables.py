"""Create core indexer tables: blocks, txs, outputs, address_stats.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "blocks",
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("hash", sa.Text(), nullable=False),
        sa.Column("prev_hash", sa.Text(), nullable=False),
        sa.Column("time", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("bits", sa.Text(), nullable=True),
        sa.Column("nonce", sa.BigInteger(), nullable=True),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=True),
        sa.Column("difficulty", sa.Numeric(), nullable=True),
        sa.Column("tx_count", sa.Integer(), nullable=False),
        sa.Column("total_out", sa.Numeric(), nullable=False),
        sa.Column("fees", sa.Numeric(), nullable=False),
        sa.PrimaryKeyConstraint("height"),
        sa.UniqueConstraint("hash"),
    )
    op.create_table(
        "txs",
        sa.Column("txid", sa.Text(), nullable=False),
        sa.Column("block_height", sa.Integer(), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("locktime", sa.BigInteger(), nullable=True),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("vsize", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=True),
        sa.Column("fee", sa.Numeric(), nullable=False),
        sa.Column("total_in", sa.Numeric(), nullable=False),
        sa.Column("total_out", sa.Numeric(), nullable=False),
        sa.ForeignKeyConstraint(["block_height"], ["blocks.height"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("txid"),
    )
    op.create_index("ix_txs_block_height", "txs", ["block_height"])
    op.create_table(
        "outputs",
        sa.Column("txid", sa.Text(), nullable=False),
        sa.Column("n", sa.Integer(), nullable=False),
        sa.Column("block_height", sa.Integer(), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("script_type", sa.Text(), nullable=False),
        sa.Column("spent_by_txid", sa.Text(), nullable=True),
        sa.Column("spent_at_height", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("txid", "n"),
    )
    op.create_index("ix_outputs_address", "outputs", ["address"])
    op.create_index("ix_outputs_block_height", "outputs", ["block_height"])
    op.create_index("ix_outputs_spent_at_height", "outputs", ["spent_at_height"])
    op.create_table(
        "address_stats",
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("balance", sa.Numeric(), nullable=False),
        sa.Column("received", sa.Numeric(), nullable=False),
        sa.Column("sent", sa.Numeric(), nullable=False),
        sa.Column("tx_count", sa.Integer(), nullable=False),
        sa.Column("first_seen_height", sa.Integer(), nullable=False),
        sa.Column("last_seen_height", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("address"),
    )


def downgrade() -> None:
    op.drop_table("address_stats")
    op.drop_index("ix_outputs_spent_at_height", table_name="outputs")
    op.drop_index("ix_outputs_block_height", table_name="outputs")
    op.drop_index("ix_outputs_address", table_name="outputs")
    op.drop_table("outputs")
    op.drop_index("ix_txs_block_height", table_name="txs")
    op.drop_table("txs")
    op.drop_table("blocks")
