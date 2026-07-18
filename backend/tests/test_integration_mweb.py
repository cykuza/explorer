"""Integration: MWEB peg-in / peg-out indexing on regtest."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from explorer import tables
from explorer.config import Settings
from explorer.db import begin, connect, create_engine
from explorer.indexer.apply import rollback_block
from explorer.indexer.sync import Syncer
from explorer.rpc import RpcClient
from tests.helpers import (
    activate_mweb,
    as_decimal,
    ensure_wallet,
    mine_to,
    mweb_address,
    wallet_rpc_url,
)

pytestmark = pytest.mark.integration


def _wallet_client(settings: Settings, name: str) -> RpcClient:
    return RpcClient(
        wallet_rpc_url(settings.rpc_url, name),
        settings.rpc_user,
        settings.rpc_password,
    )


@pytest.mark.asyncio
async def test_mweb_pegin_pegout_and_cascade(
    settings: Settings,
    rpc: RpcClient,
    clean_index: None,
) -> None:
    await ensure_wallet(rpc)
    miner = str(await rpc.call("getnewaddress"))

    # Coinbase maturity + deterministic MWEB activation (peg-in at tip==activation-1).
    tip0 = int(await rpc.call("getblockcount"))
    if tip0 < 101:
        await mine_to(rpc, miner, 101 - tip0)
    activation_height = await activate_mweb(rpc, miner)
    print(f"MWEB_ACTIVATION_BLOCKS_REQUIRED={activation_height}")

    engine = create_engine(settings)
    syncer = Syncer(settings, rpc, engine)
    await syncer.tip_walk_once()

    schema = settings.db_schema
    assert schema is not None

    suffix = uuid.uuid4().hex[:8]
    # Fresh wallets each run so leftover MWEB balances cannot turn a peg-in
    # into an MWEB-internal transfer.
    await ensure_wallet(rpc, f"transparent_src_{suffix}")
    t_rpc = _wallet_client(settings, f"transparent_src_{suffix}")
    await ensure_wallet(rpc, f"mweb_phase3_{suffix}")
    mweb_rpc = _wallet_client(settings, f"mweb_phase3_{suffix}")

    try:
        t_addr = str(await t_rpc.call("getnewaddress"))
        # Fund with a transparent send from the miner wallet (coinbase UTXOs).
        fund_txid = str(await rpc.call("sendtoaddress", t_addr, "10"))
        await mine_to(rpc, miner, 1)
        fund_raw = await rpc.call("getrawtransaction", fund_txid, True)
        assert isinstance(fund_raw, dict) and fund_raw.get("blockhash")

        mweb_addr = await mweb_address(mweb_rpc)
        pegin_amount = Decimal("1.25")
        pegin_txid = str(await t_rpc.call("sendtoaddress", mweb_addr, str(pegin_amount)))
        await mine_to(rpc, miner, 1)
        pegin_raw = await rpc.call("getrawtransaction", pegin_txid, True)
        assert isinstance(pegin_raw, dict)
        pegin_blockhash = str(pegin_raw["blockhash"])
        pegin_header = await rpc.call("getblockheader", pegin_blockhash)
        assert isinstance(pegin_header, dict)
        tip_pegin = int(pegin_header["height"])
        await syncer.tip_walk_once()

        # Confirm the funding tx produced a witness_mweb_pegin (true peg-in).
        pegin_tx = await rpc.call("getrawtransaction", pegin_txid, True)
        assert isinstance(pegin_tx, dict)
        pegin_types = [
            (vout.get("scriptPubKey") or {}).get("type")
            for vout in pegin_tx.get("vout") or []
            if isinstance(vout, dict)
        ]
        assert "witness_mweb_pegin" in pegin_types, f"not a peg-in: types={pegin_types}"

        hogex_txid: str
        async with connect(engine, schema) as conn:
            mweb_row = (
                await conn.execute(
                    select(tables.mweb_blocks).where(
                        tables.mweb_blocks.c.height == tip_pegin,
                    ),
                )
            ).one_or_none()
            assert mweb_row is not None, f"expected mweb_blocks at height {tip_pegin}"
            pegin = as_decimal(mweb_row.pegin)
            mweb_amount = as_decimal(mweb_row.mweb_amount)
            assert mweb_row.hogex_txid
            hogex_txid = str(mweb_row.hogex_txid)
            print(
                f"PEGIN_OBSERVED pegin={pegin} mweb_amount={mweb_amount} hogex_txid={hogex_txid}",
            )
            assert pegin > Decimal("0")
            assert mweb_amount > Decimal("0")

            block = await rpc.call("getblock", pegin_blockhash, 2)
            assert isinstance(block, dict)
            txs = block["tx"]
            assert isinstance(txs, list) and txs
            last = txs[-1]
            last_txid = str(last["txid"]) if isinstance(last, dict) else str(last)
            assert hogex_txid == last_txid

            hogex_flag = (
                await conn.execute(
                    select(tables.txs.c.is_hogex).where(
                        tables.txs.c.txid == hogex_txid,
                    ),
                )
            ).scalar_one()
            assert bool(hogex_flag) is True

        # Cascade: rollback tip must drop mweb_blocks + hogex tx via FK.
        async with begin(engine, schema) as roll_conn:
            await rollback_block(roll_conn, tip_pegin, network=settings.network)

        async with connect(engine, schema) as conn:
            gone = (
                await conn.execute(
                    select(func.count())
                    .select_from(tables.mweb_blocks)
                    .where(tables.mweb_blocks.c.height == tip_pegin),
                )
            ).scalar_one()
            assert int(gone) == 0
            hogex_gone = (
                await conn.execute(
                    select(func.count())
                    .select_from(tables.txs)
                    .where(tables.txs.c.txid == hogex_txid),
                )
            ).scalar_one()
            assert int(hogex_gone) == 0

        # Re-sync peg-in block after cascade check.
        await syncer.tip_walk_once()

        async with connect(engine, schema) as conn:
            restored = (
                await conn.execute(
                    select(tables.mweb_blocks).where(
                        tables.mweb_blocks.c.height == tip_pegin,
                    ),
                )
            ).one()
            amount_after_pegin = as_decimal(restored.mweb_amount)
            pegin_restored = as_decimal(restored.pegin)
            assert pegin_restored > Decimal("0")
            assert amount_after_pegin > Decimal("0")

        # --- Peg-out from the MWEB-only wallet to a canonical address ---
        # MWEB sendtoaddress returns a wallet/MWEB id that may not be a chain
        # txid until HogEx lands; locate the peg-out via tip height after mine.
        canonical = str(await rpc.call("getnewaddress"))
        pegout_amount = Decimal("0.5")
        await mweb_rpc.call("sendtoaddress", canonical, str(pegout_amount))
        await mine_to(rpc, miner, 1)
        tip_pegout = int(await rpc.call("getblockcount"))
        await syncer.tip_walk_once()

        async with connect(engine, schema) as conn:
            pegout_row = (
                await conn.execute(
                    select(tables.mweb_blocks).where(
                        tables.mweb_blocks.c.height == tip_pegout,
                    ),
                )
            ).one_or_none()
            assert pegout_row is not None, f"expected mweb_blocks at peg-out height {tip_pegout}"
            pegout = as_decimal(pegout_row.pegout)
            amount_after_pegout = as_decimal(pegout_row.mweb_amount)
            print(
                f"PEGOUT_OBSERVED pegout={pegout} mweb_amount={amount_after_pegout} "
                f"prev_mweb_amount={amount_after_pegin}",
            )
            assert pegout > Decimal("0")
            assert amount_after_pegout < amount_after_pegin
    finally:
        await t_rpc.aclose()
        await mweb_rpc.aclose()
        await engine.dispose()
