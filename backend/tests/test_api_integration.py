"""Live compose integration: API against synced regtest index + real RPC."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from explorer.api.app import create_app
from explorer.api.context import NetworkContext
from explorer.api.settings import ApiSettings
from explorer.config import Settings
from explorer.indexer.sync import Syncer
from explorer.rpc import RpcClient
from tests.helpers import ensure_wallet, mine_to

pytestmark = pytest.mark.integration


@pytest.fixture
async def synced_api(
    settings: Settings,
    rpc: RpcClient,
    clean_index: None,
    monkeypatch: pytest.MonkeyPatch,
) -> Any:
    await ensure_wallet(rpc, "testwallet")
    addr = str(await rpc.call("getnewaddress"))
    await mine_to(rpc, addr, 5)
    engine = create_async_engine(settings.db_url, pool_pre_ping=True)
    syncer = Syncer(settings, rpc, engine)
    await syncer.tip_walk_once()

    monkeypatch.setenv("EXPLORER_API_NETWORKS", "regtest")
    monkeypatch.setenv("EXPLORER_DB_URL", settings.db_url)
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_URL", settings.rpc_url)
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_USER", settings.rpc_user)
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_PASSWORD", settings.rpc_password)
    monkeypatch.setenv("EXPLORER_API_MAX_LAG", "10")

    api_settings = ApiSettings()  # type: ignore[call-arg]
    live_rpc = RpcClient(settings.rpc_url, settings.rpc_user, settings.rpc_password)
    ctx = NetworkContext(
        network="regtest",
        schema="regtest",
        engine=engine,
        rpc=live_rpc,
    )
    app = create_app(api_settings, contexts={"regtest": ctx}, engine=engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, rpc
    await live_rpc.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_live_tip_block_tx_address_mempool_mweb_search(
    synced_api: tuple[AsyncClient, RpcClient],
) -> None:
    client, rpc = synced_api

    tip = await client.get("/api/v1/regtest/tip")
    assert tip.status_code == 200
    tip_body = tip.json()
    assert tip_body["height"] >= 5

    block = await client.get(f"/api/v1/regtest/block/{tip_body['height']}")
    assert block.status_code == 200
    assert block.json()["hash"] == tip_body["hash"]

    txs = await client.get(f"/api/v1/regtest/block/{tip_body['height']}/txs")
    assert txs.status_code == 200
    assert txs.json()["total"] >= 1
    txid = txs.json()["txs"][0]["txid"]

    tx = await client.get(f"/api/v1/regtest/tx/{txid}")
    assert tx.status_code == 200
    assert tx.json()["txid"] == txid
    assert tx.json()["confirmations"] >= 1

    # Coinbase output address from tip block via node
    raw_block = await rpc.call("getblock", tip_body["hash"], 2)
    coinbase = raw_block["tx"][0]
    spk = coinbase["vout"][0]["scriptPubKey"]
    addr = spk.get("address") or (spk.get("addresses") or [None])[0]
    if addr:
        addr_r = await client.get(f"/api/v1/regtest/address/{addr}")
        assert addr_r.status_code == 200
        assert addr_r.json()["address"] == addr

    mempool = await client.get("/api/v1/regtest/mempool")
    assert mempool.status_code == 200
    assert "count" in mempool.json()

    mweb = await client.get("/api/v1/regtest/mweb/summary")
    assert mweb.status_code == 200
    assert mweb.json()["activation_height"] == 432

    search = await client.get(f"/api/v1/regtest/search/{tip_body['height']}")
    assert search.json() == {"type": "block", "id": str(tip_body["height"])}

    health = await client.get("/healthz")
    assert health.status_code == 200
    assert health.json()["networks"]["regtest"]["lag"] == 0
