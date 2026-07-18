"""Integration: reorg via invalidateblock and re-sync."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from explorer import tables
from explorer.config import Settings
from explorer.db import connect, create_engine
from explorer.indexer.sync import Syncer
from explorer.rpc import RpcClient
from tests.helpers import as_decimal, ensure_wallet, mine_to

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_reorg_invalidate_and_resync(
    settings: Settings,
    rpc: RpcClient,
    clean_index: None,
) -> None:
    await ensure_wallet(rpc)
    addr = str(await rpc.call("getnewaddress"))
    await mine_to(rpc, addr, 20)

    engine = create_engine(settings)
    syncer = Syncer(settings, rpc, engine)
    await syncer.tip_walk_once()

    tip_before = int(await rpc.call("getblockcount"))
    orphan_height = tip_before - 3
    orphan_hash = str(await rpc.call("getblockhash", orphan_height))

    schema = settings.db_schema
    assert schema is not None
    async with connect(engine, schema) as conn:
        stored_orphan = (
            await conn.execute(
                select(tables.blocks.c.hash).where(
                    tables.blocks.c.height == orphan_height,
                ),
            )
        ).scalar_one()
        assert str(stored_orphan) == orphan_hash

    await rpc.call("invalidateblock", orphan_hash)
    remine_addr = str(await rpc.call("getnewaddress"))
    await mine_to(rpc, remine_addr, 6)

    tip_after = int(await rpc.call("getblockcount"))
    new_tip_hash = str(await rpc.call("getbestblockhash"))
    assert tip_after > tip_before - 3

    await syncer.tip_walk_once()

    async with connect(engine, schema) as conn:
        db_tip_h = (
            await conn.execute(
                select(tables.sync_state.c.height).where(
                    tables.sync_state.c.network == settings.network,
                ),
            )
        ).scalar_one()
        assert int(db_tip_h) == tip_after

        db_tip_hash = (
            await conn.execute(
                select(tables.blocks.c.hash).where(tables.blocks.c.height == tip_after),
            )
        ).scalar_one()
        assert str(db_tip_hash) == new_tip_hash

        still = (
            await conn.execute(
                select(func.count())
                .select_from(tables.blocks)
                .where(tables.blocks.c.hash == orphan_hash),
            )
        ).scalar_one()
        assert int(still) == 0

        for h in range(orphan_height, tip_before + 1):
            row = (
                await conn.execute(
                    select(tables.blocks.c.hash).where(tables.blocks.c.height == h),
                )
            ).one_or_none()
            if row is not None:
                node_h = str(await rpc.call("getblockhash", h))
                assert str(row.hash) == node_h

        # Balances: every DB address_stats.balance equals sum of unspent outputs
        # in the index for that address (node listunspent omits immature coinbase).
        stats_rows = (await conn.execute(select(tables.address_stats))).all()
        for stats in stats_rows:
            unspent = (
                await conn.execute(
                    select(func.coalesce(func.sum(tables.outputs.c.value), 0)).where(
                        tables.outputs.c.address == stats.address,
                        tables.outputs.c.spent_by_txid.is_(None),
                    ),
                )
            ).scalar_one()
            assert as_decimal(stats.balance) == as_decimal(unspent)

    await engine.dispose()
