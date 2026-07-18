"""Legacy `/api/*` contract tests: exact success/failure body shapes."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from explorer.api.app import create_app
from explorer.api.context import NetworkContext
from explorer.api.legacy import clear_legacy_cache
from explorer.api.settings import ApiSettings, NetworkRpcConfig
from explorer.config import Settings
from explorer.db import begin
from explorer.indexer.apply import apply_block
from explorer.rpc import RpcClient, RpcError
from tests.test_api_app import (
    BLOCK1,
    COINBASE0,
    HOGEX_TX,
    _genesis_block,
    _mweb_block,
)

pytestmark = pytest.mark.integration

VALID_UNSEEN = "validunseenaddr"
INVALID_ADDR = "not-a-real-address"


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_legacy_cache()


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
        if method == "getmempoolinfo":
            return {"size": 2, "bytes": 500, "total_fee": Decimal("0.00010000")}
        if method == "getrawmempool":
            return []
        if method == "validateaddress":
            addr = str(params[0])
            if addr in ("alice", "bob", "miner", VALID_UNSEEN):
                return {"isvalid": True, "address": addr}
            return {"isvalid": False}
        if method == "getrawtransaction":
            txid = str(params[0])
            if txid == COINBASE0:
                return {
                    "txid": COINBASE0,
                    "version": 1,
                    "vin": [{"coinbase": "01"}],
                    "vout": [{"n": 0, "value": Decimal("50")}],
                }
            raise RpcError(-5, "No such mempool or blockchain transaction")
        if method == "getblock":
            block_hash = str(params[0])
            if block_hash == BLOCK1:
                return {
                    "hash": BLOCK1,
                    "height": 1,
                    "tx": [],
                    "mweb": {"hash": "mm" * 32},
                }
            raise RpcError(-5, "Block not found")
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


@pytest.fixture
async def empty_api_client(
    settings: Any,
    clean_index: None,
    stub_rpc: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> Any:
    """API against truncated schema (no sync_state / blocks)."""
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(settings.db_url, pool_pre_ping=True)
    monkeypatch.setenv("EXPLORER_API_NETWORKS", "regtest")
    monkeypatch.setenv("EXPLORER_DB_URL", settings.db_url)
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_URL", "http://stub")
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_USER", "u")
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_PASSWORD", "p")

    api_settings = ApiSettings()  # type: ignore[call-arg]
    api_settings.network_rpc["regtest"] = NetworkRpcConfig("http://stub", "u", "p")
    ctx = NetworkContext(
        network="regtest",
        schema="regtest",
        engine=engine,
        rpc=stub_rpc,
    )
    app = create_app(api_settings, contexts={"regtest": ctx}, engine=engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await engine.dispose()


@pytest.mark.asyncio
async def test_addressbalance_success(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/addressbalance/alice")
    assert r.status_code == 200
    assert r.json() == {"error": "ok", "message": "0.00000000"}


@pytest.mark.asyncio
async def test_addressbalance_unseen_valid(api_client: AsyncClient) -> None:
    r = await api_client.get(f"/api/addressbalance/{VALID_UNSEEN}")
    assert r.status_code == 200
    assert r.json() == {"error": "ok", "message": "0.00000000"}


@pytest.mark.asyncio
async def test_addressbalance_invalid(api_client: AsyncClient) -> None:
    r = await api_client.get(f"/api/addressbalance/{INVALID_ADDR}")
    assert r.status_code == 200
    assert r.json() == {"error": "404", "message": "This address is invalid"}


@pytest.mark.asyncio
async def test_receivedbyaddress_success(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/receivedbyaddress/alice")
    assert r.status_code == 200
    assert r.json() == {"error": "ok", "message": "50.00000000"}


@pytest.mark.asyncio
async def test_receivedbyaddress_invalid(api_client: AsyncClient) -> None:
    r = await api_client.get(f"/api/receivedbyaddress/{INVALID_ADDR}")
    assert r.status_code == 200
    assert r.json() == {"error": "404", "message": "This address is invalid"}


@pytest.mark.asyncio
async def test_sentbyaddress_success(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/sentbyaddress/alice")
    assert r.status_code == 200
    assert r.json() == {"error": "ok", "message": "50.00000000"}


@pytest.mark.asyncio
async def test_sentbyaddress_invalid(api_client: AsyncClient) -> None:
    r = await api_client.get(f"/api/sentbyaddress/{INVALID_ADDR}")
    assert r.status_code == 200
    assert r.json() == {"error": "404", "message": "This address is invalid"}


@pytest.mark.asyncio
async def test_validateaddress_success(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/validateaddress/alice")
    assert r.status_code == 200
    assert r.json() == {"error": "ok", "message": "valid"}


@pytest.mark.asyncio
async def test_validateaddress_failure(api_client: AsyncClient) -> None:
    r = await api_client.get(f"/api/validateaddress/{INVALID_ADDR}")
    assert r.status_code == 200
    assert r.json() == {
        "error": "this string cannot be verified as an address",
        "message": "invalid",
    }


@pytest.mark.asyncio
async def test_rawtx_success(api_client: AsyncClient) -> None:
    r = await api_client.get(f"/api/rawtx/{COINBASE0}")
    assert r.status_code == 200
    body = r.json()
    assert body["txid"] == COINBASE0
    assert "error" not in body


@pytest.mark.asyncio
async def test_rawtx_failure(api_client: AsyncClient) -> None:
    r = await api_client.get(f"/api/rawtx/{HOGEX_TX}")
    assert r.status_code == 200
    assert r.json() == {
        "error": "invalid",
        "message": "This transaction is invalid",
    }


@pytest.mark.asyncio
async def test_block_success(api_client: AsyncClient) -> None:
    r = await api_client.get(f"/api/block/{BLOCK1}")
    assert r.status_code == 200
    body = r.json()
    assert body["hash"] == BLOCK1
    assert "mweb" in body
    assert "error" not in body


@pytest.mark.asyncio
async def test_block_failure(api_client: AsyncClient) -> None:
    r = await api_client.get(f"/api/block/{'ff' * 32}")
    assert r.status_code == 200
    assert r.json() == {
        "error": "invalid",
        "message": "This transaction is invalid",
    }


@pytest.mark.asyncio
async def test_getbestblockhash_success(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/block/getbestblockhash")
    assert r.status_code == 200
    assert r.json() == BLOCK1


@pytest.mark.asyncio
async def test_getbestblockhash_failure(empty_api_client: AsyncClient) -> None:
    r = await empty_api_client.get("/api/block/getbestblockhash")
    assert r.status_code == 200
    assert r.json() == {
        "error": "404",
        "message": "There was a JSON error. Try again later",
    }


@pytest.mark.asyncio
async def test_getblockcount_success(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/block/getblockcount")
    assert r.status_code == 200
    assert r.json() == {"error": "ok", "message": "1"}


@pytest.mark.asyncio
async def test_getblockcount_failure(empty_api_client: AsyncClient) -> None:
    r = await empty_api_client.get("/api/block/getblockcount")
    assert r.status_code == 200
    assert r.json() == {
        "error": "404",
        "message": "There was a JSON error. Try again later",
    }


@pytest.mark.asyncio
async def test_getsummary_success(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/getsummary")
    assert r.status_code == 200
    # coinbases 50+50 − block fees 10.2 = 89.8
    assert r.json() == {"error": "ok", "message": "89.80000000"}


@pytest.mark.asyncio
async def test_getsummary_failure(empty_api_client: AsyncClient) -> None:
    r = await empty_api_client.get("/api/getsummary")
    assert r.status_code == 200
    assert r.json() == {
        "error": "404",
        "message": "There was a JSON error. Try again later",
    }


@pytest.mark.asyncio
async def test_totaltransactions_success(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/totaltransactions")
    assert r.status_code == 200
    assert r.json() == {"error": "ok", "message": "4"}


@pytest.mark.asyncio
async def test_totaltransactions_failure(empty_api_client: AsyncClient) -> None:
    r = await empty_api_client.get("/api/totaltransactions")
    assert r.status_code == 200
    assert r.json() == {
        "error": "404",
        "message": "There was a JSON error. Try again later",
    }


@pytest.mark.asyncio
async def test_confirmations_success(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/confirmations/0")
    assert r.status_code == 200
    assert r.json() == {"error": "ok", "message": "2"}


@pytest.mark.asyncio
async def test_confirmations_failure(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/confirmations/99")
    assert r.status_code == 200
    assert r.json() == {
        "error": "404",
        "message": "There was a JSON error. Try again later",
    }


@pytest.mark.asyncio
async def test_lastdifficulty_success(api_client: AsyncClient) -> None:
    r = await api_client.get("/api/lastdifficulty")
    assert r.status_code == 200
    assert r.json() == {"error": "ok", "message": "1.50000000"}


@pytest.mark.asyncio
async def test_lastdifficulty_failure(empty_api_client: AsyncClient) -> None:
    r = await empty_api_client.get("/api/lastdifficulty")
    assert r.status_code == 200
    assert r.json() == {
        "error": "404",
        "message": "There was a JSON error. Try again later",
    }
