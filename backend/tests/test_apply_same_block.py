"""Unit tests for same-block prevout resolution in apply_block."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from explorer.indexer.apply import apply_block


def _spk(address: str) -> dict[str, Any]:
    return {"addresses": [address], "type": "pubkeyhash", "address": address}


def _same_block_fixture() -> dict[str, Any]:
    """Block where tx2 spends tx1's output created earlier in the same block."""
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
                        "value": Decimal("49"),
                        "scriptPubKey": _spk("alice"),
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
                        "value": Decimal("48"),
                        "scriptPubKey": _spk("bob"),
                    },
                ],
            },
        ],
    }


def _mock_conn() -> AsyncMock:
    result = MagicMock()
    result.one_or_none.return_value = None
    result.all.return_value = []
    result.scalar_one.return_value = 0
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=result)
    return conn


@pytest.mark.asyncio
async def test_same_block_spend_resolves_prevout(monkeypatch: pytest.MonkeyPatch) -> None:
    """tx2 spending tx1 in the same block must not raise IndexIntegrityError."""
    funding_key = ("0" * 64, 0)
    funding = {funding_key: (Decimal("50"), "funder")}

    async def fake_get_block_hash(_conn: object, height: int) -> str | None:
        assert height == 0
        return "a" * 64

    async def fake_load_prevouts(
        _conn: object,
        keys: list[tuple[str, int]],
    ) -> dict[tuple[str, int], tuple[Decimal, str | None]]:
        return {k: funding[k] for k in keys if k in funding}

    monkeypatch.setattr(
        "explorer.indexer.apply.get_block_hash",
        fake_get_block_hash,
    )
    monkeypatch.setattr(
        "explorer.indexer.apply._load_prevouts",
        fake_load_prevouts,
    )

    conn = _mock_conn()
    block = _same_block_fixture()

    await apply_block(conn, block, network="regtest")

    # Spend-marking update must run for the same-block prevout (tx1:0 by tx2).
    update_sql = [str(call.args[0]) for call in conn.execute.await_args_list if call.args]
    assert any("spent_by_txid" in sql or "UPDATE" in sql.upper() for sql in update_sql)
