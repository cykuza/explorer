"""Unit tests for RpcClient against httpx MockTransport."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from explorer.rpc import RpcClient, RpcError, RpcHttpError


def _handler(request: httpx.Request) -> httpx.Response:
    body: dict[str, Any] = json.loads(request.content.decode())
    method = body["method"]
    if method == "getblockchaininfo":
        return httpx.Response(
            200,
            json={
                "result": {"chain": "regtest", "blocks": 0},
                "error": None,
                "id": body["id"],
            },
        )
    if method == "fail":
        return httpx.Response(
            200,
            json={
                "result": None,
                "error": {"code": -32601, "message": "Method not found"},
                "id": body["id"],
            },
        )
    if method == "boom":
        return httpx.Response(500, text="internal error")
    return httpx.Response(
        200,
        json={"result": None, "error": None, "id": body["id"]},
    )


@pytest.fixture
async def rpc() -> RpcClient:
    transport = httpx.MockTransport(_handler)
    client = httpx.AsyncClient(transport=transport)
    return RpcClient("http://rpc.test", "dev", "dev", client=client)


async def test_call_success(rpc: RpcClient) -> None:
    result = await rpc.call("getblockchaininfo")
    assert result == {"chain": "regtest", "blocks": 0}
    await rpc.aclose()


async def test_call_rpc_error(rpc: RpcClient) -> None:
    with pytest.raises(RpcError) as exc_info:
        await rpc.call("fail")
    assert exc_info.value.code == -32601
    assert "Method not found" in exc_info.value.message
    await rpc.aclose()


async def test_call_http_error(rpc: RpcClient) -> None:
    with pytest.raises(RpcHttpError) as exc_info:
        await rpc.call("boom")
    assert exc_info.value.status_code == 500
    await rpc.aclose()
