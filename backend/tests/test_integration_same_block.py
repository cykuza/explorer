"""Integration: same-block spend (tx B spends tx A in one mined block)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from explorer import tables
from explorer.config import Settings
from explorer.db import connect, create_engine
from explorer.indexer.sync import Syncer
from explorer.rpc import RpcClient
from tests.helpers import as_decimal, ensure_wallet, mine_to

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_same_block_chained_txs(
    settings: Settings,
    rpc: RpcClient,
    clean_index: None,
) -> None:
    await ensure_wallet(rpc)
    addr_fund = str(await rpc.call("getnewaddress"))
    addr_a = str(await rpc.call("getnewaddress"))
    addr_b = str(await rpc.call("getnewaddress"))

    tip = int(await rpc.call("getblockcount"))
    if tip < 101:
        await mine_to(rpc, addr_fund, 101 - tip)

    await rpc.call("sendtoaddress", addr_a, "10")
    await mine_to(rpc, addr_fund, 1)

    unspent = await rpc.call("listunspent", 1, 9999999, [addr_a])
    assert isinstance(unspent, list) and unspent
    utxo = unspent[0]

    raw_a = await rpc.call(
        "createrawtransaction",
        [{"txid": utxo["txid"], "vout": int(utxo["vout"])}],
        [{addr_a: "5"}],
    )
    funded_a = await rpc.call("fundrawtransaction", raw_a)
    signed_a = await rpc.call("signrawtransactionwithwallet", funded_a["hex"])
    assert signed_a.get("complete") is True
    txid_a = str(await rpc.call("sendrawtransaction", signed_a["hex"]))

    decoded_a = await rpc.call("decoderawtransaction", signed_a["hex"])
    vout_a: int | None = None
    for out in decoded_a["vout"]:
        spk = out.get("scriptPubKey") or {}
        addrs = list(spk.get("addresses") or [])
        if not addrs and spk.get("address"):
            addrs = [spk["address"]]
        if addr_a in addrs and as_decimal(out["value"]) == Decimal("5"):
            vout_a = int(out["n"])
            break
    assert vout_a is not None

    # Spend A's 5-CY output → 4.999 to addr_b (0.001 fee, under maxfeerate).
    raw_b = await rpc.call(
        "createrawtransaction",
        [{"txid": txid_a, "vout": vout_a}],
        [{addr_b: "4.999"}],
    )
    signed_b = await rpc.call("signrawtransactionwithwallet", raw_b)
    assert signed_b.get("complete") is True
    txid_b = str(await rpc.call("sendrawtransaction", signed_b["hex"]))

    await mine_to(rpc, addr_fund, 1)
    tip = int(await rpc.call("getblockcount"))
    tip_hash = str(await rpc.call("getblockhash", tip))
    block = await rpc.call("getblock", tip_hash, 2)
    block_txids = [str(tx["txid"]) for tx in block["tx"]]
    assert txid_a in block_txids
    assert txid_b in block_txids
    assert block_txids.index(txid_a) < block_txids.index(txid_b)

    engine = create_engine(settings)
    syncer = Syncer(settings, rpc, engine)
    await syncer.tip_walk_once()

    schema = settings.db_schema
    assert schema is not None
    async with connect(engine, schema) as conn:
        assert (
            await conn.execute(select(tables.txs.c.txid).where(tables.txs.c.txid == txid_a))
        ).one_or_none() is not None
        assert (
            await conn.execute(select(tables.txs.c.txid).where(tables.txs.c.txid == txid_b))
        ).one_or_none() is not None

        spent = (
            await conn.execute(
                select(
                    tables.outputs.c.spent_by_txid,
                    tables.outputs.c.spent_at_height,
                ).where(
                    tables.outputs.c.txid == txid_a,
                    tables.outputs.c.n == vout_a,
                ),
            )
        ).one()
        assert str(spent.spent_by_txid) == txid_b
        assert int(spent.spent_at_height) == tip

        stats_b = (
            await conn.execute(
                select(
                    tables.address_stats.c.received,
                    tables.address_stats.c.balance,
                ).where(tables.address_stats.c.address == addr_b),
            )
        ).one()
        assert as_decimal(stats_b.received) == Decimal("4.999")
        assert as_decimal(stats_b.balance) == Decimal("4.999")

    await engine.dispose()
