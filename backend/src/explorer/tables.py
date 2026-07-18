"""SQLAlchemy Core table definitions for the explorer index."""

from __future__ import annotations

import sqlalchemy as sa

metadata = sa.MetaData()

sync_state = sa.Table(
    "sync_state",
    metadata,
    sa.Column("network", sa.Text(), primary_key=True),
    sa.Column("height", sa.Integer(), nullable=False),
    sa.Column("tip_hash", sa.Text(), nullable=False),
    sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    ),
)

blocks = sa.Table(
    "blocks",
    metadata,
    sa.Column("height", sa.Integer(), primary_key=True),
    sa.Column("hash", sa.Text(), nullable=False, unique=True),
    sa.Column("prev_hash", sa.Text(), nullable=False),
    sa.Column("time", sa.Integer(), nullable=False),
    sa.Column("version", sa.Integer()),
    sa.Column("bits", sa.Text()),
    sa.Column("nonce", sa.BigInteger()),
    sa.Column("size", sa.Integer()),
    sa.Column("weight", sa.Integer()),
    sa.Column("difficulty", sa.Numeric()),
    sa.Column("tx_count", sa.Integer(), nullable=False),
    sa.Column("total_out", sa.Numeric(), nullable=False),
    sa.Column("fees", sa.Numeric(), nullable=False),
)

txs = sa.Table(
    "txs",
    metadata,
    sa.Column("txid", sa.Text(), primary_key=True),
    sa.Column(
        "block_height",
        sa.Integer(),
        sa.ForeignKey("blocks.height", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    sa.Column("idx", sa.Integer(), nullable=False),
    sa.Column("version", sa.Integer()),
    sa.Column("locktime", sa.BigInteger()),
    sa.Column("size", sa.Integer()),
    sa.Column("vsize", sa.Integer()),
    sa.Column("weight", sa.Integer()),
    sa.Column("fee", sa.Numeric(), nullable=False),
    sa.Column("total_in", sa.Numeric(), nullable=False),
    sa.Column("total_out", sa.Numeric(), nullable=False),
    sa.Column(
        "is_hogex",
        sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    ),
)

mweb_blocks = sa.Table(
    "mweb_blocks",
    metadata,
    sa.Column(
        "height",
        sa.Integer(),
        sa.ForeignKey("blocks.height", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column("hash", sa.Text(), nullable=False),
    sa.Column("kernel_offset", sa.Text()),
    sa.Column("stealth_offset", sa.Text()),
    sa.Column("num_kernels", sa.Integer(), nullable=False),
    sa.Column("num_txos", sa.Integer(), nullable=False),
    sa.Column("kernel_root", sa.Text()),
    sa.Column("output_root", sa.Text()),
    sa.Column("leaf_root", sa.Text()),
    sa.Column("mweb_amount", sa.Numeric(), nullable=False),
    sa.Column("pegin", sa.Numeric(), nullable=False),
    sa.Column("pegout", sa.Numeric(), nullable=False),
    sa.Column("kernel_fees", sa.Numeric(), nullable=False),
    sa.Column("hogex_txid", sa.Text()),
)

outputs = sa.Table(
    "outputs",
    metadata,
    sa.Column("txid", sa.Text(), nullable=False),
    sa.Column("n", sa.Integer(), nullable=False),
    sa.Column("block_height", sa.Integer(), nullable=False, index=True),
    sa.Column("value", sa.Numeric(), nullable=False),
    sa.Column("address", sa.Text(), index=True),
    sa.Column("script_type", sa.Text(), nullable=False),
    sa.Column("spent_by_txid", sa.Text()),
    sa.Column("spent_at_height", sa.Integer(), index=True),
    sa.PrimaryKeyConstraint("txid", "n"),
)

address_stats = sa.Table(
    "address_stats",
    metadata,
    sa.Column("address", sa.Text(), primary_key=True),
    sa.Column("balance", sa.Numeric(), nullable=False),
    sa.Column("received", sa.Numeric(), nullable=False),
    sa.Column("sent", sa.Numeric(), nullable=False),
    sa.Column("tx_count", sa.Integer(), nullable=False),
    sa.Column("first_seen_height", sa.Integer(), nullable=False),
    sa.Column("last_seen_height", sa.Integer(), nullable=False),
)
