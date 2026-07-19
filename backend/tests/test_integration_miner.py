"""Integration: miner bootstrap/steady against live regtest."""

from __future__ import annotations

import asyncio

import pytest

from explorer.chain import predict_mweb_activation_height
from explorer.config import Settings
from explorer.miner import (
    COINBASE_MATURITY,
    Miner,
    MinerSettings,
    select_miner_mode,
)
from explorer.rpc import RpcClient

pytestmark = pytest.mark.integration

# Fresh regtest may still report mweb ``defined`` (activation=None) until enough
# blocks land in the first period. Cap ticks so CI cannot hang.
_MAX_AWAIT_ACTIVATION_TICKS = 40


@pytest.mark.asyncio
async def test_miner_bootstrap_or_steady(rpc: RpcClient, settings: Settings) -> None:
    """Drive one miner path from live tip: await activation, boundary, or steady.

    Shared regtest is often past MWEB activation (steady). Fresh CI compose may
    still have mweb ``defined`` — exercise the await-activation bootstrap branch
    first. If tip can still reach ``activation - 1`` within a modest budget,
    cross the boundary; otherwise assert steady/bootstrap tip advance.
    """
    miner_settings = MinerSettings(
        network="regtest",
        rpc_url=settings.rpc_url,
        rpc_user=settings.rpc_user,
        rpc_password=settings.rpc_password,
        miner_bootstrap_sleep_sec=0,
        miner_interval_sec=1,
    )

    stop = asyncio.Event()
    root = RpcClient(settings.rpc_url, settings.rpc_user, settings.rpc_password)
    miner = Miner(miner_settings, root, stop_event=stop, sleep=_noop_sleep)
    try:
        await miner.bootstrap_wallet()

        info = await miner.rpc.call("getblockchaininfo")
        assert isinstance(info, dict)
        tip = int(info["blocks"])
        activation = predict_mweb_activation_height(info)
        path_prefix = ""

        if activation is None:
            path_prefix = "await_activation+"
            print(f"MINER_INTEGRATION_PATH=await_activation tip={tip} activation=None")
            for _ in range(_MAX_AWAIT_ACTIVATION_TICKS):
                tip_before = int(await miner.rpc.call("getblockcount"))
                ok = await miner.tick_once()
                assert ok
                tip_after = int(await miner.rpc.call("getblockcount"))
                assert tip_after > tip_before, (
                    f"await_activation expected tip advance, {tip_before} -> {tip_after}"
                )
                info = await miner.rpc.call("getblockchaininfo")
                assert isinstance(info, dict)
                tip = int(info["blocks"])
                activation = predict_mweb_activation_height(info)
                if activation is not None:
                    break
            assert activation is not None, (
                f"mweb still defined after {_MAX_AWAIT_ACTIVATION_TICKS} miner ticks (tip={tip})"
            )

        mode = select_miner_mode(tip, activation)
        distance_to_boundary = (activation - 1) - tip
        can_cross_boundary = 0 <= distance_to_boundary <= 200

        if can_cross_boundary:
            path = f"{path_prefix}boundary"
            print(f"MINER_INTEGRATION_PATH={path} tip={tip} activation={activation}")
            while True:
                info2 = await miner.rpc.call("getblockchaininfo")
                assert isinstance(info2, dict)
                tip2 = int(info2["blocks"])
                if tip2 >= activation:
                    break
                if tip2 == activation - 1:
                    ok = await miner.tick_once()
                    assert ok
                    tip_after = int(await miner.rpc.call("getblockcount"))
                    assert tip_after >= activation, (
                        f"expected tip >= {activation} after boundary tick, got {tip_after}"
                    )
                    break
                ok = await miner.tick_once()
                assert ok
                tip3 = int(await miner.rpc.call("getblockcount"))
                assert tip3 > tip2 or tip2 == activation - 1
            return

        if mode == "steady" or tip >= activation + COINBASE_MATURITY:
            path = f"{path_prefix}steady"
            print(
                f"MINER_INTEGRATION_PATH={path} tip={tip} activation={activation} mode={mode}",
            )
            tip_before = int(await miner.rpc.call("getblockcount"))
            ok = await miner.tick_once()
            assert ok
            tip_after = int(await miner.rpc.call("getblockcount"))
            assert tip_after == tip_before + 1, (
                f"steady path expected +1 block, {tip_before} -> {tip_after}"
            )
            return

        path = f"{path_prefix}bootstrap_post_activation"
        tip_before = int(await miner.rpc.call("getblockcount"))
        ok = await miner.tick_once()
        assert ok
        tip_after = int(await miner.rpc.call("getblockcount"))
        assert tip_after > tip_before, (
            f"bootstrap path expected tip advance, {tip_before} -> {tip_after}"
        )
        print(
            f"MINER_INTEGRATION_PATH={path} tip_before={tip_before} "
            f"tip_after={tip_after} activation={activation}",
        )
    finally:
        stop.set()
        await miner.rpc.aclose()


async def _noop_sleep(_sec: float) -> None:
    return None
