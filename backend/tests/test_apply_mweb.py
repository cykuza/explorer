"""Unit tests for MWEB indexing in apply_block / rollback_block."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from explorer import tables
from explorer.indexer.apply import apply_block, rollback_block


def _spk(address: str) -> dict[str, Any]:
    return {"addresses": [address], "type": "pubkeyhash", "address": address}


def _mweb_fixture() -> dict[str, Any]:
    """Block with two vkern-bearing txs and HogEx last."""
    return {
        "hash": "b" * 64,
        "previousblockhash": "a" * 64,
        "height": 1,
        "time": 1_700_000_000,
        "version": 1,
        "bits": "207fffff",
        "nonce": 0,
        "size": 500,
        "weight": 2000,
        "difficulty": Decimal("1"),
        "mweb_amount": Decimal("15.5"),
        "mweb": {
            "hash": "m" * 64,
            "height": 1,
            "kernel_offset": "ko",
            "stealth_offset": "so",
            "num_kernels": 3,
            "num_txos": 4,
            "kernel_root": "kr",
            "output_root": "or",
            "leaf_root": "lr",
        },
        "tx": [
            {
                "txid": "c" * 64,
                "version": 1,
                "locktime": 0,
                "size": 100,
                "vsize": 100,
                "weight": 400,
                "vin": [{"coinbase": "01", "sequence": 0xFFFFFFFF}],
                "vout": [
                    {
                        "n": 0,
                        "value": Decimal("50"),
                        "scriptPubKey": _spk("miner"),
                    },
                ],
            },
            {
                "txid": "1" * 64,
                "version": 1,
                "locktime": 0,
                "size": 200,
                "vsize": 200,
                "weight": 800,
                "vin": [
                    {
                        "txid": "0" * 64,
                        "vout": 0,
                        "sequence": 0xFFFFFFFF,
                    },
                ],
                "vout": [
                    {
                        "n": 0,
                        "value": Decimal("40"),
                        "scriptPubKey": _spk("alice"),
                    },
                ],
                "vkern": [
                    {
                        "kernel_id": "k1",
                        "fee": Decimal("0.1"),
                        "pegin": Decimal("10"),
                        "pegout": [],
                    },
                ],
            },
            {
                "txid": "2" * 64,
                "version": 1,
                "locktime": 0,
                "size": 200,
                "vsize": 200,
                "weight": 800,
                "vin": [
                    {
                        "txid": "1" * 64,
                        "vout": 0,
                        "sequence": 0xFFFFFFFF,
                    },
                ],
                "vout": [
                    {
                        "n": 0,
                        "value": Decimal("39"),
                        "scriptPubKey": _spk("bob"),
                    },
                ],
                "vkern": [
                    {
                        "kernel_id": "k2",
                        "fee": Decimal("0.05"),
                        "pegin": Decimal("0"),
                        "pegout": [
                            {
                                "value": Decimal("2.5"),
                                "scriptPubKey": "0014abcd",
                            },
                        ],
                    },
                ],
            },
            {
                "txid": "h" * 64,
                "version": 1,
                "locktime": 0,
                "size": 300,
                "vsize": 300,
                "weight": 1200,
                "vin": [
                    {
                        "txid": "f" * 64,
                        "vout": 0,
                        "sequence": 0xFFFFFFFF,
                    },
                ],
                "vout": [
                    {
                        "n": 0,
                        "value": Decimal("15.5"),
                        "scriptPubKey": {
                            "type": "witness_v9_mweb",
                            "hex": "51",
                        },
                    },
                    {
                        "n": 1,
                        "value": Decimal("2.5"),
                        "scriptPubKey": _spk("pegout"),
                    },
                ],
                "vkern": [
                    {
                        "kernel_id": "k3",
                        "fee": Decimal("0.02"),
                        "pegin": Decimal("5.5"),
                        "pegout": [],
                    },
                ],
            },
        ],
    }


def _no_mweb_fixture() -> dict[str, Any]:
    block = _mweb_fixture()
    del block["mweb"]
    del block["mweb_amount"]
    for tx in block["tx"]:
        tx.pop("vkern", None)
    return block


def _mock_conn() -> AsyncMock:
    result = MagicMock()
    result.one_or_none.return_value = None
    result.all.return_value = []
    result.scalar_one.return_value = 0
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=result)
    return conn


def _find_tx_rows(conn: AsyncMock) -> list[dict[str, Any]]:
    for call in conn.execute.await_args_list:
        if len(call.args) >= 2 and isinstance(call.args[1], list):
            rows = call.args[1]
            if rows and isinstance(rows[0], dict) and "is_hogex" in rows[0]:
                return rows
    return []


def _find_mweb_values(conn: AsyncMock) -> dict[str, Any] | None:
    for call in conn.execute.await_args_list:
        if not call.args:
            continue
        stmt = call.args[0]
        if not hasattr(stmt, "compile"):
            continue
        if "mweb_blocks" not in str(stmt).lower():
            continue
        compiled = stmt.compile()
        if compiled.params and "mweb_amount" in compiled.params:
            return dict(compiled.params)
    return None


@pytest.mark.asyncio
async def test_mweb_block_aggregates_and_hogex(monkeypatch: pytest.MonkeyPatch) -> None:
    funding = {
        ("0" * 64, 0): (Decimal("50"), "funder"),
        ("f" * 64, 0): (Decimal("20"), "funder2"),
    }

    async def fake_get_block_hash(_conn: object, height: int) -> str | None:
        assert height == 0
        return "a" * 64

    async def fake_load_prevouts(
        _conn: object,
        keys: list[tuple[str, int]],
    ) -> dict[tuple[str, int], tuple[Decimal, str | None]]:
        return {k: funding[k] for k in keys if k in funding}

    monkeypatch.setattr("explorer.indexer.apply.get_block_hash", fake_get_block_hash)
    monkeypatch.setattr("explorer.indexer.apply._load_prevouts", fake_load_prevouts)

    conn = _mock_conn()
    await apply_block(conn, _mweb_fixture(), network="regtest")

    tx_rows = _find_tx_rows(conn)
    assert len(tx_rows) == 4
    assert [r["is_hogex"] for r in tx_rows] == [False, False, False, True]
    assert tx_rows[-1]["txid"] == "h" * 64

    mweb = _find_mweb_values(conn)
    assert mweb is not None
    assert mweb["height"] == 1
    assert mweb["hash"] == "m" * 64
    assert mweb["kernel_offset"] == "ko"
    assert mweb["stealth_offset"] == "so"
    assert mweb["num_kernels"] == 3
    assert mweb["num_txos"] == 4
    assert mweb["kernel_root"] == "kr"
    assert mweb["output_root"] == "or"
    assert mweb["leaf_root"] == "lr"
    assert mweb["mweb_amount"] == Decimal("15.5")
    # pegin: 10 + 0 + 5.5 = 15.5; pegout: 2.5; fees: 0.1 + 0.05 + 0.02 = 0.17
    assert mweb["pegin"] == Decimal("15.5")
    assert mweb["pegout"] == Decimal("2.5")
    assert mweb["kernel_fees"] == Decimal("0.17")
    assert mweb["hogex_txid"] == "h" * 64


@pytest.mark.asyncio
async def test_block_without_mweb_skips_mweb_row(monkeypatch: pytest.MonkeyPatch) -> None:
    funding = {
        ("0" * 64, 0): (Decimal("50"), "funder"),
        ("f" * 64, 0): (Decimal("20"), "funder2"),
    }

    async def fake_get_block_hash(_conn: object, height: int) -> str | None:
        return "a" * 64

    async def fake_load_prevouts(
        _conn: object,
        keys: list[tuple[str, int]],
    ) -> dict[tuple[str, int], tuple[Decimal, str | None]]:
        return {k: funding[k] for k in keys if k in funding}

    monkeypatch.setattr("explorer.indexer.apply.get_block_hash", fake_get_block_hash)
    monkeypatch.setattr("explorer.indexer.apply._load_prevouts", fake_load_prevouts)

    conn = _mock_conn()
    await apply_block(conn, _no_mweb_fixture(), network="regtest")

    tx_rows = _find_tx_rows(conn)
    assert tx_rows
    assert all(r["is_hogex"] is False for r in tx_rows)

    for call in conn.execute.await_args_list:
        if not call.args:
            continue
        stmt = call.args[0]
        if hasattr(stmt, "compile") and "mweb_blocks" in str(stmt).lower():
            pytest.fail("mweb_blocks insert must not run for non-mweb blocks")


def test_mweb_blocks_fk_cascade() -> None:
    fks = list(tables.mweb_blocks.foreign_keys)
    assert len(fks) == 1
    assert fks[0].column is tables.blocks.c.height
    assert fks[0].ondelete == "CASCADE"


@pytest.mark.asyncio
async def test_rollback_deletes_blocks_not_mweb_explicitly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cascade covers mweb_blocks; rollback must not DELETE mweb_blocks itself."""
    funding = {
        ("0" * 64, 0): (Decimal("50"), "funder"),
        ("f" * 64, 0): (Decimal("20"), "funder2"),
    }

    async def fake_get_block_hash(_conn: object, height: int) -> str | None:
        if height == 0:
            return "a" * 64
        if height == 1:
            return "b" * 64
        return None

    async def fake_load_prevouts(
        _conn: object,
        keys: list[tuple[str, int]],
    ) -> dict[tuple[str, int], tuple[Decimal, str | None]]:
        return {k: funding[k] for k in keys if k in funding}

    monkeypatch.setattr("explorer.indexer.apply.get_block_hash", fake_get_block_hash)
    monkeypatch.setattr("explorer.indexer.apply._load_prevouts", fake_load_prevouts)

    conn = _mock_conn()
    await apply_block(conn, _mweb_fixture(), network="regtest")
    conn.execute.reset_mock()

    # collect_block_deltas reads outputs; return empty so reverse is a no-op.
    empty = MagicMock()
    empty.all.return_value = []
    empty.one_or_none.return_value = None
    empty.scalar_one.return_value = 0
    conn.execute = AsyncMock(return_value=empty)

    await rollback_block(conn, 1, network="regtest")

    sqls = [str(call.args[0]).lower() for call in conn.execute.await_args_list if call.args]
    assert any("blocks" in sql and "delete" in sql for sql in sqls)
    assert not any("mweb_blocks" in sql and "delete" in sql for sql in sqls)
