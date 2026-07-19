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


@pytest.mark.asyncio
async def test_miner_bootstrap_or_steady(rpc: RpcClient, settings: Settings) -> None:
    """Drive one miner path from live tip: activation boundary or steady single block.

    Shared regtest is usually past MWEB activation; prefer steady. If tip can still
    reach ``activation - 1``, mine across the boundary instead.
    """
    info = await rpc.call("getblockchaininfo")
    assert isinstance(info, dict)
    tip = int(info["blocks"])
    activation = predict_mweb_activation_height(info)
    assert activation is not None, "regtest mweb should be predictable after compose start"

    miner_settings = MinerSettings(
        network="regtest",
        rpc_url=settings.rpc_url,
        rpc_user=settings.rpc_user,
        rpc_password=settings.rpc_password,
        miner_bootstrap_sleep_sec=0,
        miner_interval_sec=1,
    )

    # Use a dedicated wallet so we do not disturb testwallet state unnecessarily.
    stop = asyncio.Event()
    root = RpcClient(settings.rpc_url, settings.rpc_user, settings.rpc_password)
    miner = Miner(miner_settings, root, stop_event=stop, sleep=_noop_sleep)
    try:
        await miner.bootstrap_wallet()
        mode = select_miner_mode(tip, activation)
        distance_to_boundary = (activation - 1) - tip

        # Prefer boundary path only when we can reach it with a modest number of
        # ticks (batch 25) without hour-long runs on a cold chain.
        can_cross_boundary = 0 <= distance_to_boundary <= 200

        if can_cross_boundary:
            path = "boundary"
            print(
                f"MINER_INTEGRATION_PATH={path} tip={tip} activation={activation}",
            )
            # Approach until tip == activation - 1, then one activation tick.
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
                # Safety: avoid infinite loop if tip stalls.
                tip3 = int(await miner.rpc.call("getblockcount"))
                assert tip3 > tip2 or tip2 == activation - 1
        else:
            path = "steady"
            print(
                f"MINER_INTEGRATION_PATH={path} tip={tip} activation={activation} "
                f"mode={mode}",
            )
            # If still in bootstrap past activation, advance with miner ticks until
            # steady, then mine exactly one steady block — or mine one bootstrap
            # block and assert tip advanced by the batch size.
            if mode == "steady" or tip >= activation + COINBASE_MATURITY:
                tip_before = int(await miner.rpc.call("getblockcount"))
                ok = await miner.tick_once()
                assert ok
                tip_after = int(await miner.rpc.call("getblockcount"))
                assert tip_after == tip_before + 1, (
                    f"steady path expected +1 block, {tip_before} -> {tip_after}"
                )
            else:
                # Past activation but still bootstrap: one tick must advance tip.
                tip_before = int(await miner.rpc.call("getblockcount"))
                ok = await miner.tick_once()
                assert ok
                tip_after = int(await miner.rpc.call("getblockcount"))
                assert tip_after > tip_before, (
                    f"bootstrap path expected tip advance, {tip_before} -> {tip_after}"
                )
                path = "bootstrap_post_activation"
                print(
                    f"MINER_INTEGRATION_PATH={path} tip_before={tip_before} "
                    f"tip_after={tip_after} activation={activation}",
                )
    finally:
        stop.set()
        await miner.rpc.aclose()


async def _noop_sleep(_sec: float) -> None:
    return None
