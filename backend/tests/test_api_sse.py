"""SSE `/api/v1/{network}/events` stream tests (real uvicorn; ASGITransport buffers forever)."""

from __future__ import annotations

import asyncio
import contextlib
import json
import socket
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest
import uvicorn
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from explorer.api.app import create_app
from explorer.api.context import NetworkContext
from explorer.api.settings import ApiSettings, NetworkRpcConfig
from explorer.api.sse import _active_stream_tasks
from explorer.config import Settings
from explorer.db import begin
from explorer.indexer.apply import apply_block
from explorer.rpc import RpcClient
from tests.test_api_app import BLOCK1, _genesis_block, _mweb_block

pytestmark = pytest.mark.integration

BLOCK2 = "cc" * 32
COINBASE2 = "55" * 32


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _block2() -> dict[str, Any]:
    return {
        "hash": BLOCK2,
        "previousblockhash": BLOCK1,
        "height": 2,
        "time": 1_700_000_200,
        "version": 1,
        "bits": "207fffff",
        "nonce": 2,
        "size": 200,
        "weight": 800,
        "difficulty": Decimal("2"),
        "tx": [
            {
                "txid": COINBASE2,
                "version": 1,
                "locktime": 0,
                "size": 100,
                "vsize": 100,
                "weight": 400,
                "vin": [{"coinbase": "03", "sequence": 0xFFFFFFFF}],
                "vout": [
                    {
                        "n": 0,
                        "value": Decimal("50"),
                        "scriptPubKey": {
                            "addresses": ["miner2"],
                            "type": "pubkeyhash",
                            "address": "miner2",
                        },
                    },
                ],
            },
        ],
    }


def _consume_sse(buffer: str) -> tuple[list[tuple[str, dict[str, Any] | None]], str]:
    """Split complete SSE frames from buffer; return (events, remainder)."""
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
            return {"size": 1, "bytes": 100, "total_fee": Decimal("0")}
        if method == "getrawmempool":
            return []
        raise AssertionError(f"unexpected RPC {method} {params}")

    rpc.call = AsyncMock(side_effect=call)
    rpc.aclose = AsyncMock()
    return rpc


@pytest.fixture
async def sse_server(
    api_engine: Any,
    stub_rpc: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> Any:
    monkeypatch.setenv("EXPLORER_API_NETWORKS", "regtest")
    monkeypatch.setenv("EXPLORER_DB_URL", str(api_engine.url))
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_URL", "http://stub")
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_USER", "u")
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_PASSWORD", "p")
    monkeypatch.setenv("EXPLORER_API_SSE_POLL_SEC", "0.05")

    settings = ApiSettings()  # type: ignore[call-arg]
    settings.network_rpc["regtest"] = NetworkRpcConfig("http://stub", "u", "p")
    ctx = NetworkContext(
        network="regtest",
        schema="regtest",
        engine=api_engine,
        rpc=stub_rpc,
    )
    app = create_app(settings, contexts={"regtest": ctx}, engine=api_engine)
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    base = f"http://127.0.0.1:{port}"
    # Wait until the server accepts connections
    for _ in range(100):
        if server.started:
            break
        await asyncio.sleep(0.02)
    assert server.started, "uvicorn failed to start"
    yield base, api_engine
    server.should_exit = True
    await task


@pytest.mark.asyncio
async def test_sse_initial_tip_then_change(sse_server: Any) -> None:
    base, engine = sse_server

    async def seed_after_delay() -> None:
        await asyncio.sleep(0.2)
        async with begin(engine, "regtest") as conn:
            await apply_block(conn, _block2(), network="regtest")

    seed_task = asyncio.create_task(seed_after_delay())
    buffer = ""
    tip_events: list[dict[str, Any]] = []
    deadline = asyncio.get_running_loop().time() + 5.0

    try:
        async with (
            AsyncClient(base_url=base, timeout=10.0) as client,
            client.stream("GET", "/api/v1/regtest/events") as response,
        ):
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            async for chunk in response.aiter_text():
                buffer += chunk
                frames, buffer = _consume_sse(buffer)
                for name, data in frames:
                    if name == "tip" and data is not None:
                        tip_events.append(data)

                if any(e.get("height") == 2 for e in tip_events):
                    break
                if asyncio.get_running_loop().time() > deadline:
                    break
    finally:
        if not seed_task.done():
            seed_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await seed_task
        else:
            await seed_task

    assert tip_events, "expected at least the initial tip event"
    assert tip_events[0]["height"] == 1
    assert tip_events[0]["hash"] == BLOCK1
    assert any(e["height"] == 2 and e["hash"] == BLOCK2 for e in tip_events)


@pytest.mark.asyncio
async def test_sse_cancels_poll_task_on_disconnect(sse_server: Any) -> None:
    base, _engine = sse_server
    before = set(_active_stream_tasks)

    async with (
        AsyncClient(base_url=base, timeout=10.0) as client,
        client.stream("GET", "/api/v1/regtest/events") as response,
    ):
        assert response.status_code == 200
        for _ in range(100):
            new_tasks = _active_stream_tasks - before
            if new_tasks:
                break
            await asyncio.sleep(0.02)
        new_tasks = _active_stream_tasks - before
        assert new_tasks, "expected an active SSE stream task"
        tracked = list(new_tasks)
        async for chunk in response.aiter_text():
            if chunk:
                break

    for _ in range(100):
        if not (_active_stream_tasks & set(tracked)):
            break
        await asyncio.sleep(0.02)

    assert not (_active_stream_tasks & set(tracked))
