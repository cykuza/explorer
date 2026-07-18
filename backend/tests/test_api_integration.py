"""Live compose integration: API against synced regtest index + real RPC."""

from __future__ import annotations

import asyncio
import contextlib
import json
import socket
from typing import Any

import pytest
import uvicorn
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


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


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
    monkeypatch.setenv("EXPLORER_API_SSE_POLL_SEC", "0.2")

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
        yield {
            "client": client,
            "rpc": rpc,
            "engine": engine,
            "syncer": syncer,
            "settings": settings,
            "miner": addr,
            "app": app,
        }
    await live_rpc.aclose()
    await engine.dispose()


def _consume_sse(buffer: str) -> tuple[list[tuple[str, dict[str, Any] | None]], str]:
    events: list[tuple[str, dict[str, Any] | None]] = []
    while "\n\n" in buffer:
        frame, buffer = buffer.split("\n\n", 1)
        frame = frame.strip("\n")
        if not frame:
            continue
        if frame.startswith(":"):
            events.append(("comment", None))
            continue
        event_name = "message"
        data_line: str | None = None
        for line in frame.split("\n"):
            if line.startswith("event:"):
                event_name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_line = line[len("data:") :].strip()
        if data_line is not None:
            events.append((event_name, json.loads(data_line)))
    return events, buffer


@pytest.mark.asyncio
async def test_live_tip_block_tx_address_mempool_mweb_search(
    synced_api: dict[str, Any],
) -> None:
    client = synced_api["client"]
    rpc = synced_api["rpc"]

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


@pytest.mark.asyncio
async def test_live_sse_tip_after_mine(synced_api: dict[str, Any]) -> None:
    # Real HTTP required: httpx ASGITransport buffers infinite streams forever.
    app = synced_api["app"]
    rpc = synced_api["rpc"]
    syncer = synced_api["syncer"]
    miner = synced_api["miner"]
    asgi_client = synced_api["client"]

    tip0 = (await asgi_client.get("/api/v1/regtest/tip")).json()
    start_height = int(tip0["height"])

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    serve_task = asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:
            break
        await asyncio.sleep(0.02)
    assert server.started

    async def mine_after_delay() -> None:
        await asyncio.sleep(0.5)
        await mine_to(rpc, miner, 1)
        await syncer.tip_walk_once()

    mine_task = asyncio.create_task(mine_after_delay())
    buffer = ""
    tip_events: list[dict[str, Any]] = []
    deadline = asyncio.get_running_loop().time() + 30.0
    base = f"http://127.0.0.1:{port}"

    try:
        async with (
            AsyncClient(base_url=base, timeout=30.0) as client,
            client.stream("GET", "/api/v1/regtest/events") as response,
        ):
            assert response.status_code == 200
            async for chunk in response.aiter_text():
                buffer += chunk
                frames, buffer = _consume_sse(buffer)
                for name, data in frames:
                    if name == "tip" and data is not None:
                        tip_events.append(data)

                if any(e.get("height", 0) > start_height for e in tip_events):
                    break
                if asyncio.get_running_loop().time() > deadline:
                    break
    finally:
        if not mine_task.done():
            mine_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await mine_task
        else:
            await mine_task
        server.should_exit = True
        await serve_task

    assert tip_events, "expected initial tip SSE event"
    assert tip_events[0]["height"] == start_height
    assert any(e["height"] == start_height + 1 for e in tip_events)


@pytest.mark.asyncio
async def test_live_legacy_happy_path(synced_api: dict[str, Any]) -> None:
    client = synced_api["client"]
    rpc = synced_api["rpc"]
    miner = synced_api["miner"]

    tip = (await client.get("/api/v1/regtest/tip")).json()
    tip_hash = tip["hash"]
    tip_height = tip["height"]

    count = await client.get("/api/block/getblockcount")
    assert count.status_code == 200
    assert count.json() == {"error": "ok", "message": str(tip_height)}

    best = await client.get("/api/block/getbestblockhash")
    assert best.status_code == 200
    assert best.json() == tip_hash

    bal = await client.get(f"/api/addressbalance/{miner}")
    assert bal.status_code == 200
    body = bal.json()
    assert body["error"] == "ok"
    assert "." in body["message"]

    raw_block = await rpc.call("getblock", tip_hash, 2)
    coinbase_txid = raw_block["tx"][0]["txid"]
    rawtx = await client.get(f"/api/rawtx/{coinbase_txid}")
    assert rawtx.status_code == 200
    assert rawtx.json()["txid"] == coinbase_txid

    valid = await client.get(f"/api/validateaddress/{miner}")
    assert valid.status_code == 200
    assert valid.json() == {"error": "ok", "message": "valid"}
