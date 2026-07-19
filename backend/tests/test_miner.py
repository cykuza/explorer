"""Unit tests for miner mode selection, mainnet guard, and activation recovery."""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from explorer.__main__ import main
from explorer.miner import (
    MinerSettings,
    activation_boundary_action,
    mine_activation_block,
    run_miner,
    select_miner_mode,
)
from explorer.rpc import RpcError


def test_select_miner_mode_bootstrap_until_activation_plus_maturity() -> None:
    activation = 432
    assert select_miner_mode(0, activation) == "bootstrap"
    assert select_miner_mode(activation - 1, activation) == "bootstrap"
    assert select_miner_mode(activation, activation) == "bootstrap"
    assert select_miner_mode(activation + 99, activation) == "bootstrap"
    assert select_miner_mode(activation + 100, activation) == "steady"
    assert select_miner_mode(activation + 500, activation) == "steady"


def test_activation_boundary_action() -> None:
    activation = 2880
    assert activation_boundary_action(0, activation) == "approach"
    assert activation_boundary_action(activation - 2, activation) == "approach"
    assert activation_boundary_action(activation - 1, activation) == "activation_boundary"
    assert activation_boundary_action(activation, activation) == "post_activation"
    assert activation_boundary_action(activation + 50, activation) == "post_activation"
    assert activation_boundary_action(activation + 100, activation) == "steady"


def test_miner_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPLORER_NETWORK", "testnet")
    monkeypatch.setenv("EXPLORER_RPC_URL", "http://127.0.0.1:44549")
    monkeypatch.setenv("EXPLORER_RPC_USER", "u")
    monkeypatch.setenv("EXPLORER_RPC_PASSWORD", "p")
    for key in (
        "EXPLORER_MINER_BOOTSTRAP_SLEEP_SEC",
        "EXPLORER_MINER_INTERVAL_SEC",
        "EXPLORER_ZMQ_RAWBLOCK",
        "EXPLORER_DB_URL",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = MinerSettings()  # type: ignore[call-arg]
    assert settings.network == "testnet"
    assert settings.miner_bootstrap_sleep_sec == 5
    assert settings.miner_interval_sec == 600


def test_miner_settings_missing_rpc_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPLORER_NETWORK", "testnet")
    monkeypatch.delenv("EXPLORER_RPC_URL", raising=False)
    monkeypatch.delenv("EXPLORER_RPC_USER", raising=False)
    monkeypatch.delenv("EXPLORER_RPC_PASSWORD", raising=False)
    with pytest.raises(ValidationError):
        MinerSettings()  # type: ignore[call-arg]


def test_mainnet_guard_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPLORER_NETWORK", "mainnet")
    monkeypatch.setenv("EXPLORER_RPC_URL", "http://127.0.0.1:58382")
    monkeypatch.setenv("EXPLORER_RPC_USER", "u")
    monkeypatch.setenv("EXPLORER_RPC_PASSWORD", "p")
    assert main(["miner"]) == 2


@pytest.mark.asyncio
async def test_run_miner_mainnet_raises() -> None:
    settings = MinerSettings(
        network="mainnet",
        rpc_url="http://127.0.0.1:58382",
        rpc_user="u",
        rpc_password="p",
    )
    with pytest.raises(SystemExit, match="mainnet"):
        await run_miner(settings)


@pytest.mark.asyncio
async def test_mine_activation_recovers_from_vin_empty(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """First generatetoaddress fails with bad-txns-vin-empty; second peg+mine succeeds."""
    activation = 50
    tip = activation - 1
    generate_calls = 0
    pegins: list[str] = []
    mempool: list[str] = []

    async def call(method: str, *params: Any) -> Any:
        nonlocal generate_calls, tip
        if method == "getblockcount":
            return tip
        if method == "getnewaddress":
            return "mweb1testaddr"
        if method == "sendtoaddress":
            txid = f"pegin{len(pegins) + 1}"
            pegins.append(txid)
            mempool.clear()
            mempool.append(txid)
            return txid
        if method == "getrawmempool":
            return list(mempool)
        if method == "generatetoaddress":
            generate_calls += 1
            if generate_calls == 1:
                raise RpcError(-26, "bad-txns-vin-empty")
            tip = activation
            mempool.clear()
            return ["hash_activation"]
        raise AssertionError(f"unexpected RPC {method} {params}")

    rpc = MagicMock()
    rpc.call = AsyncMock(side_effect=call)
    sleeps: list[float] = []

    async def fake_sleep(sec: float) -> None:
        sleeps.append(sec)

    # Avoid real wait_pegin_in_mempool delays.
    async def instant_wait(rpc_arg: Any, txid: str, **_kwargs: Any) -> bool:
        mempool_now = await rpc_arg.call("getrawmempool")
        return isinstance(mempool_now, list) and txid in mempool_now

    monkeypatch.setattr("explorer.miner.wait_pegin_in_mempool", instant_wait)

    with caplog.at_level(logging.WARNING, logger="explorer.miner"):
        hashes = await mine_activation_block(
            rpc,
            "mineraddr",
            activation,
            sleep=fake_sleep,
        )

    assert hashes == ["hash_activation"]
    assert len(pegins) == 2
    assert generate_calls == 2
    assert sleeps  # backoff after stall
    assert any("miner_activation_stall" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_mine_activation_requires_mempool_before_mine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    activation = 50
    tip = activation - 1
    peg_count = 0
    generate_calls = 0

    async def call(method: str, *params: Any) -> Any:
        nonlocal peg_count, generate_calls, tip
        if method == "getblockcount":
            return tip
        if method == "getnewaddress":
            return "mweb1testaddr"
        if method == "sendtoaddress":
            peg_count += 1
            return f"txid{peg_count}"
        if method == "getrawmempool":
            # Only the second peg-in is visible.
            return ["txid2"] if peg_count >= 2 else []
        if method == "generatetoaddress":
            generate_calls += 1
            tip = activation
            return ["h"]
        raise AssertionError(f"unexpected RPC {method}")

    rpc = MagicMock()
    rpc.call = AsyncMock(side_effect=call)

    async def fake_sleep(_sec: float) -> None:
        return None

    wait_calls = 0

    async def controlled_wait(rpc_arg: Any, txid: str, **_kwargs: Any) -> bool:
        nonlocal wait_calls
        wait_calls += 1
        mempool_now = await rpc_arg.call("getrawmempool")
        return isinstance(mempool_now, list) and txid in mempool_now

    monkeypatch.setattr("explorer.miner.wait_pegin_in_mempool", controlled_wait)

    hashes = await mine_activation_block(rpc, "addr", activation, sleep=fake_sleep)
    assert hashes == ["h"]
    assert peg_count == 2
    assert generate_calls == 1
    assert wait_calls == 2
