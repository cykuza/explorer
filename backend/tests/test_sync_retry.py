"""Unit tests for indexer node-unreachable retry (connection-class RPC errors)."""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from explorer.indexer.sync import Syncer
from explorer.rpc import RpcError, RpcHttpError, is_rpc_connection_error


def test_is_rpc_connection_error() -> None:
    assert is_rpc_connection_error(RpcHttpError(0, "[Errno -2] Name or service not known"))
    assert is_rpc_connection_error(RpcHttpError(0, "Connection refused"))
    assert not is_rpc_connection_error(RpcHttpError(500, "internal error"))
    assert not is_rpc_connection_error(RpcError(-32601, "Method not found"))
    assert not is_rpc_connection_error(RuntimeError("boom"))


def _make_syncer() -> Syncer:
    settings = MagicMock()
    settings.db_schema = "regtest"
    settings.network = "regtest"
    settings.sync_poll_interval_sec = 60.0
    settings.max_reorg_depth = 100
    return Syncer(settings, MagicMock(), MagicMock())


@pytest.mark.asyncio
async def test_run_retries_connection_errors_then_recovers(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    syncer = _make_syncer()
    calls = {"n": 0}

    async def flaky_walk() -> int:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RpcHttpError(0, "[Errno -2] Name or service not known")
        return 0

    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(syncer, "tip_walk_once", flaky_walk)
    monkeypatch.setattr("explorer.indexer.sync.asyncio.sleep", fake_sleep)

    with caplog.at_level(logging.INFO, logger="explorer.indexer.sync"):
        await syncer.run(once=True)

    assert calls["n"] == 3
    assert sleeps == [1.0, 2.0]
    assert any(r.getMessage() == "node_unreachable" for r in caplog.records)
    assert any(r.getMessage() == "node_recovered" for r in caplog.records)
    assert any(r.getMessage() == "backfill_done" for r in caplog.records)


@pytest.mark.asyncio
async def test_run_fail_fast_on_non_connection_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    syncer = _make_syncer()

    async def bad_walk() -> int:
        raise RpcHttpError(500, "internal error")

    monkeypatch.setattr(syncer, "tip_walk_once", bad_walk)
    monkeypatch.setattr(
        "explorer.indexer.sync.asyncio.sleep",
        AsyncMock(side_effect=AssertionError("must not sleep on non-conn error")),
    )

    with pytest.raises(RpcHttpError) as exc_info:
        await syncer.run(once=True)
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_run_fail_fast_on_rpc_error(monkeypatch: pytest.MonkeyPatch) -> None:
    syncer = _make_syncer()

    async def bad_walk() -> Any:
        raise RpcError(-5, "Block not found")

    monkeypatch.setattr(syncer, "tip_walk_once", bad_walk)

    with pytest.raises(RpcError):
        await syncer.run(once=True)
