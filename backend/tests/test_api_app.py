"""App-level ASGI tests: seeded regtest schema + stubbed RpcClient."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from explorer.api.app import create_app
from explorer.api.context import NetworkContext
from explorer.api.settings import ApiSettings, NetworkRpcConfig
from explorer.config import Settings
from explorer.db import begin
from explorer.indexer.apply import apply_block
from explorer.rpc import RpcClient, RpcError

pytestmark = pytest.mark.integration

GENESIS = "aa" * 32
BLOCK1 = "bb" * 32
COINBASE0 = "11" * 32
COINBASE1 = "22" * 32
SPEND_TX = "33" * 32
HOGEX_TX = "44" * 32


def _spk(address: str) -> dict[str, Any]:
    return {"addresses": [address], "type": "pubkeyhash", "address": address}


def _genesis_block() -> dict[str, Any]:
    return {
        "hash": GENESIS,
        "previousblockhash": "00" * 32,
        "height": 0,
        "time": 1_700_000_000,
        "version": 1,
        "bits": "207fffff",
        "nonce": 0,
        "size": 200,
        "weight": 800,
        "difficulty": Decimal("1"),
        "tx": [
            {
                "txid": COINBASE0,
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
                        "scriptPubKey": _spk("alice"),
                    },
                ],
            },
        ],
    }


def _mweb_block() -> dict[str, Any]:
    return {
        "hash": BLOCK1,
        "previousblockhash": GENESIS,
        "height": 1,
        "time": 1_700_000_100,
        "version": 1,
        "bits": "207fffff",
        "nonce": 1,
        "size": 500,
        "weight": 2000,
        "difficulty": Decimal("1.5"),
        "mweb_amount": Decimal("10"),
        "mweb": {
            "hash": "mm" * 32,
            "height": 1,
            "kernel_offset": "ko",
            "stealth_offset": "so",
            "num_kernels": 1,
            "num_txos": 2,
            "kernel_root": "kr",
            "output_root": "or",
            "leaf_root": "lr",
        },
        "tx": [
            {
                "txid": COINBASE1,
                "version": 1,
                "locktime": 0,
                "size": 100,
                "vsize": 100,
                "weight": 400,
                "vin": [{"coinbase": "02", "sequence": 0xFFFFFFFF}],
                "vout": [
                    {
                        "n": 0,
                        "value": Decimal("50"),
                        "scriptPubKey": _spk("miner"),
                    },
                ],
            },
            {
                "txid": SPEND_TX,
                "version": 1,
                "locktime": 0,
                "size": 200,
                "vsize": 200,
                "weight": 800,
                "vin": [
                    {
                        "txid": COINBASE0,
                        "vout": 0,
                        "sequence": 0xFFFFFFFF,
                        "scriptSig": {"asm": "sig", "hex": "00"},
                    },
                ],
                "vout": [
                    {
                        "n": 0,
                        "value": Decimal("39.9"),
                        "scriptPubKey": _spk("bob"),
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
                "txid": HOGEX_TX,
                "version": 1,
                "locktime": 0,
                "size": 300,
                "vsize": 300,
                "weight": 1200,
                "vin": [
                    {
                        "txid": COINBASE1,
                        "vout": 0,
                        "sequence": 0xFFFFFFFF,
                    },
                ],
                "vout": [
                    {
                        "n": 0,
                        "value": Decimal("10"),
                        "scriptPubKey": {
                            "type": "witness_v9_mweb",
                            "hex": "51",
                        },
                    },
                    {
                        "n": 1,
                        "value": Decimal("39.9"),
                        "scriptPubKey": _spk("miner"),
                    },
                ],
                "vkern": [
                    {
                        "kernel_id": "k2",
                        "fee": Decimal("0.1"),
                        "pegin": Decimal("0"),
                        "pegout": [],
                    },
                ],
            },
        ],
    }


@pytest.fixture
async def api_engine(settings: Settings, clean_index: None) -> Any:
    engine = create_async_engine(settings.db_url, pool_pre_ping=True)
    schema = settings.db_schema
    assert schema is not None
    async with begin(engine, schema) as conn:
        await apply_block(conn, _genesis_block(), network="regtest")
        await apply_block(conn, _mweb_block(), network="regtest")
    yield engine
    await engine.dispose()


@pytest.fixture
def stub_rpc() -> AsyncMock:
    rpc = AsyncMock(spec=RpcClient)

    async def call(method: str, *params: Any) -> Any:
        if method == "getblockcount":
            return 1
        if method == "getblockchaininfo":
            return {
                "blocks": 1,
                "headers": 1,
                "initialblockdownload": False,
            }
        if method == "getmempoolinfo":
            return {"size": 2, "bytes": 500, "total_fee": Decimal("0.00010000")}
        if method == "getrawmempool":
            return ["mp" + "0" * 62, "mp" + "1" * 62]
        if method == "getrawtransaction":
            txid = str(params[0])
            if txid == COINBASE0:
                return {
                    "txid": COINBASE0,
                    "hash": COINBASE0,
                    "version": 1,
                    "size": 100,
                    "vsize": 100,
                    "weight": 400,
                    "locktime": 0,
                    "vin": [{"coinbase": "01", "sequence": 0xFFFFFFFF}],
                    "vout": [
                        {
                            "n": 0,
                            "value": Decimal("50"),
                            "scriptPubKey": _spk("alice"),
                        },
                    ],
                    "hex": "0100",
                    "blockhash": GENESIS,
                    "confirmations": 2,
                    "time": 1_700_000_000,
                    "blocktime": 1_700_000_000,
                }
            if txid == HOGEX_TX:
                return {
                    "txid": HOGEX_TX,
                    "hash": HOGEX_TX,
                    "version": 1,
                    "size": 300,
                    "vsize": 300,
                    "weight": 1200,
                    "locktime": 0,
                    "vin": [
                        {
                            "txid": COINBASE1,
                            "vout": 0,
                            "scriptSig": {"asm": "", "hex": ""},
                            "sequence": 0xFFFFFFFF,
                        },
                    ],
                    "vout": [
                        {
                            "n": 0,
                            "value": Decimal("10"),
                            "scriptPubKey": {"type": "witness_v9_mweb", "hex": "51"},
                        },
                        {
                            "n": 1,
                            "value": Decimal("39.9"),
                            "scriptPubKey": _spk("miner"),
                        },
                    ],
                    "hex": "0102",
                    "blockhash": BLOCK1,
                    "confirmations": 1,
                    "time": 1_700_000_100,
                    "blocktime": 1_700_000_100,
                }
            if txid == SPEND_TX:
                return {
                    "txid": SPEND_TX,
                    "hash": SPEND_TX,
                    "version": 1,
                    "size": 200,
                    "vsize": 200,
                    "weight": 800,
                    "locktime": 0,
                    "vin": [
                        {
                            "txid": COINBASE0,
                            "vout": 0,
                            "scriptSig": {"asm": "sig", "hex": "00"},
                            "sequence": 0xFFFFFFFF,
                        },
                    ],
                    "vout": [
                        {
                            "n": 0,
                            "value": Decimal("39.9"),
                            "scriptPubKey": _spk("bob"),
                        },
                    ],
                    "hex": "0101",
                    "blockhash": BLOCK1,
                }
            raise RpcError(-5, "No such mempool or blockchain transaction")
        raise AssertionError(f"unexpected RPC {method} {params}")

    rpc.call = AsyncMock(side_effect=call)
    rpc.aclose = AsyncMock()
    return rpc


@pytest.fixture
async def api_client(
    api_engine: AsyncEngine,
    stub_rpc: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> Any:
    monkeypatch.setenv("EXPLORER_API_NETWORKS", "regtest")
    monkeypatch.setenv("EXPLORER_DB_URL", str(api_engine.url))
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_URL", "http://stub")
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_USER", "u")
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_PASSWORD", "p")
    monkeypatch.setenv("EXPLORER_API_MAX_LAG", "10")

    settings = ApiSettings()  # type: ignore[call-arg]
    settings.network_rpc["regtest"] = NetworkRpcConfig("http://stub", "u", "p")
    ctx = NetworkContext(
        network="regtest",
        schema="regtest",
        engine=api_engine,
        rpc=stub_rpc,
    )
    app = create_app(settings, contexts={"regtest": ctx}, engine=api_engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_tip(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/v1/regtest/tip")
    assert r.status_code == 200
    body = r.json()
    assert body["height"] == 1
    assert body["hash"] == BLOCK1
    assert body["time"] == 1_700_000_100


@pytest.mark.asyncio
async def test_blocks(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/v1/regtest/blocks", params={"limit": 10})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert body[0]["height"] == 1
    assert body[0]["has_mweb"] is True
    assert body[0]["fees"].endswith("000000")
    assert body[1]["has_mweb"] is False


@pytest.mark.asyncio
async def test_block_with_mweb(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/v1/regtest/block/1")
    assert r.status_code == 200
    body = r.json()
    assert body["hash"] == BLOCK1
    assert body["prev_hash"] == GENESIS
    assert body["next_hash"] is None
    assert body["mweb"] is not None
    assert body["mweb"]["mweb_amount"] == "10.00000000"
    assert body["mweb"]["hogex_txid"] == HOGEX_TX


@pytest.mark.asyncio
async def test_block_txs(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/v1/regtest/block/1/txs")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    hogex = [t for t in body["txs"] if t["is_hogex"]]
    assert len(hogex) == 1
    assert hogex[0]["txid"] == HOGEX_TX


@pytest.mark.asyncio
async def test_tx_hogex(api_client: AsyncClient) -> None:
    r = await api_client.get(f"/api/v1/regtest/tx/{HOGEX_TX}")
    assert r.status_code == 200
    body = r.json()
    assert body["is_hogex"] is True
    assert body["block_height"] == 1
    assert body["confirmations"] == 1
    assert body["vin"][0]["prevout"]["address"] == "miner"
    assert body["fee"] is not None
    assert "spent_by_txid" in body["vout"][0]
    assert body["vout"][1]["spent_by_txid"] is None


@pytest.mark.asyncio
async def test_tx_spent_by_txid(api_client: AsyncClient) -> None:
    spent = await api_client.get(f"/api/v1/regtest/tx/{COINBASE0}")
    assert spent.status_code == 200
    assert spent.json()["vout"][0]["spent_by_txid"] == SPEND_TX

    unspent = await api_client.get(f"/api/v1/regtest/tx/{SPEND_TX}")
    assert unspent.status_code == 200
    assert unspent.json()["vout"][0]["spent_by_txid"] is None


@pytest.mark.asyncio
async def test_address(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/v1/regtest/address/alice")
    assert r.status_code == 200
    body = r.json()
    assert body["address"] == "alice"
    assert body["tx_count"] >= 1


@pytest.mark.asyncio
async def test_address_txs(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/v1/regtest/address/alice/txs")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert any(t["txid"] == COINBASE0 for t in body["txs"])
    assert all("delta" in t for t in body["txs"])


@pytest.mark.asyncio
async def test_mempool(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/v1/regtest/mempool")
    assert r.status_code == 200
    assert r.json() == {
        "count": 2,
        "vsize": 500,
        "total_fee": "0.00010000",
    }


@pytest.mark.asyncio
async def test_mempool_txs(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/v1/regtest/mempool/txs", params={"limit": 1})
    assert r.status_code == 200
    assert len(r.json()["txids"]) == 1


@pytest.mark.asyncio
async def test_mweb_summary(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/v1/regtest/mweb/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["activation_height"] == 432
    assert body["latest"] is not None
    assert body["mweb_amount"] == "10.00000000"


@pytest.mark.asyncio
async def test_charts(api_client: AsyncClient) -> None:
    r = await api_client.get(
        "/api/v1/regtest/stats/charts",
        params={"metric": "tx_count", "from": 0, "to": 1},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert body[0]["height"] == 0


@pytest.mark.asyncio
async def test_search(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/v1/regtest/search/1")
    assert r.json() == {"type": "block", "id": "1"}
    r = await api_client.get(f"/api/v1/regtest/search/{BLOCK1}")
    assert r.json() == {"type": "block", "id": BLOCK1}
    r = await api_client.get(f"/api/v1/regtest/search/{HOGEX_TX}")
    assert r.json() == {"type": "tx", "id": HOGEX_TX}
    r = await api_client.get("/api/v1/regtest/search/alice")
    assert r.json() == {"type": "address", "id": "alice"}


@pytest.mark.asyncio
async def test_healthz(api_client: AsyncClient) -> None:
    r = await api_client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    net = body["networks"]["regtest"]
    assert net["lag"] == 0
    assert net["db_height"] == 1
    assert net["node_height"] == 1
    assert net["node_headers"] == 1
    assert net["ibd"] is False


@pytest.mark.asyncio
async def test_healthz_ibd_returns_503(
    api_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rpc = AsyncMock(spec=RpcClient)

    async def call(method: str, *params: Any) -> Any:
        if method == "getblockchaininfo":
            return {
                "blocks": 1,
                "headers": 100,
                "initialblockdownload": True,
            }
        raise AssertionError(f"unexpected RPC {method}")

    rpc.call = AsyncMock(side_effect=call)
    rpc.aclose = AsyncMock()

    monkeypatch.setenv("EXPLORER_API_NETWORKS", "regtest")
    monkeypatch.setenv("EXPLORER_DB_URL", str(api_engine.url))
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_URL", "http://stub")
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_USER", "u")
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_PASSWORD", "p")
    monkeypatch.setenv("EXPLORER_API_MAX_LAG", "10")

    settings = ApiSettings()  # type: ignore[call-arg]
    settings.network_rpc["regtest"] = NetworkRpcConfig("http://stub", "u", "p")
    ctx = NetworkContext(
        network="regtest",
        schema="regtest",
        engine=api_engine,
        rpc=rpc,
    )
    app = create_app(settings, contexts={"regtest": ctx}, engine=api_engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/healthz")
    assert r.status_code == 503
    net = r.json()["networks"]["regtest"]
    assert net["ibd"] is True
    assert net["lag"] == 0
    assert net["node_height"] == 1
    assert net["node_headers"] == 100


@pytest.mark.asyncio
async def test_unknown_network_problem(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/v1/mainnet/tip")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["status"] == 404
    assert body["title"] == "Not Found"
    assert "mainnet" in body["detail"]


@pytest.mark.asyncio
async def test_missing_block_problem(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/v1/regtest/block/999")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["status"] == 404


@pytest.mark.asyncio
async def test_validation_problem(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/v1/regtest/blocks", params={"limit": 999})
    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["status"] == 422
