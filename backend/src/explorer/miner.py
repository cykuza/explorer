"""Testnet/regtest miner sidecar: bootstrap through MWEB activation, then steady mining."""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from explorer.chain import predict_mweb_activation_height
from explorer.config import Network
from explorer.logging_setup import log_extra
from explorer.rpc import RpcClient, RpcError, RpcHttpError, is_rpc_connection_error
from explorer.wallet import (
    ensure_wallet,
    mine_to,
    mweb_address,
    rpc_root_url,
    wallet_rpc_url,
)

logger = logging.getLogger(__name__)

WALLET_NAME = "explorer-miner"
ADDRESS_LABEL = "explorer-miner"
COINBASE_MATURITY = 100
BOOTSTRAP_BATCH = 25
PEGIN_AMOUNT = "1"

_NODE_RETRY_INITIAL_SEC = 1.0
_NODE_RETRY_MAX_SEC = 60.0
_STALL_RETRY_INITIAL_SEC = 1.0
_STALL_RETRY_MAX_SEC = 30.0

MinerMode = Literal["bootstrap", "steady"]
BoundaryAction = Literal["approach", "activation_boundary", "post_activation", "steady"]


class MinerSettings(BaseSettings):
    """RPC-only settings for ``explorer miner`` (no DB / ZMQ)."""

    model_config = SettingsConfigDict(
        env_prefix="EXPLORER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    network: Network
    rpc_url: str
    rpc_user: str
    rpc_password: str
    miner_bootstrap_sleep_sec: int = Field(default=5, ge=0)
    miner_interval_sec: int = Field(default=600, ge=1)


def select_miner_mode(tip: int, activation: int) -> MinerMode:
    """Bootstrap until tip reaches activation + coinbase maturity, else steady."""
    if tip < activation + COINBASE_MATURITY:
        return "bootstrap"
    return "steady"


def activation_boundary_action(tip: int, activation: int) -> BoundaryAction:
    """Decide how the miner should treat the current tip relative to activation."""
    if tip >= activation + COINBASE_MATURITY:
        return "steady"
    if tip == activation - 1:
        return "activation_boundary"
    if tip < activation - 1:
        return "approach"
    return "post_activation"


def is_activation_stall_error(exc: BaseException) -> bool:
    return isinstance(exc, RpcError) and "bad-txns-vin-empty" in exc.message.lower()


async def resolve_mining_address(rpc: RpcClient) -> str:
    """Return the labeled mining address, creating it once if missing."""
    try:
        labeled = await rpc.call("getaddressesbylabel", ADDRESS_LABEL)
    except RpcError:
        labeled = None
    if isinstance(labeled, dict) and labeled:
        return str(next(iter(labeled.keys())))
    addr = str(await rpc.call("getnewaddress", ADDRESS_LABEL, "bech32"))
    return addr


async def submit_activation_pegin(rpc: RpcClient) -> str:
    """Submit an MWEB peg-in and return its txid. Caller must verify mempool."""
    dest = await mweb_address(rpc)
    txid = str(await rpc.call("sendtoaddress", dest, PEGIN_AMOUNT))
    log_extra(
        logger,
        logging.INFO,
        "miner_pegin",
        txid=txid,
        address=dest,
        amount=PEGIN_AMOUNT,
    )
    return txid


async def wait_pegin_in_mempool(
    rpc: RpcClient,
    txid: str,
    *,
    attempts: int = 10,
    delay_sec: float = 0.2,
) -> bool:
    """Return True if ``txid`` appears in ``getrawmempool`` within ``attempts`` polls."""
    for _ in range(attempts):
        mempool = await rpc.call("getrawmempool")
        if isinstance(mempool, list) and txid in mempool:
            return True
        await asyncio.sleep(delay_sec)
    return False


async def mine_activation_block(
    rpc: RpcClient,
    address: str,
    activation: int,
    *,
    sleep: Any = asyncio.sleep,
) -> list[str]:
    """Stall-proof activation: peg-in, verify mempool, mine; recover on vin-empty.

    Loops until the activation block is mined. Never raises on ``bad-txns-vin-empty``.
    """
    delay = _STALL_RETRY_INITIAL_SEC
    while True:
        tip = int(await rpc.call("getblockcount"))
        if tip >= activation:
            return []
        if tip != activation - 1:
            raise RuntimeError(
                f"mine_activation_block expected tip=={activation - 1}, got {tip}",
            )

        txid = await submit_activation_pegin(rpc)
        if not await wait_pegin_in_mempool(rpc, txid):
            log_extra(
                logger,
                logging.WARNING,
                "miner_activation_stall",
                reason="pegin_not_in_mempool",
                txid=txid,
                tip=tip,
                sleep_sec=delay,
            )
            await sleep(delay)
            delay = min(delay * 2, _STALL_RETRY_MAX_SEC)
            continue

        try:
            hashes = await mine_to(rpc, address, 1)
        except RpcError as exc:
            if not is_activation_stall_error(exc):
                raise
            log_extra(
                logger,
                logging.WARNING,
                "miner_activation_stall",
                reason="bad-txns-vin-empty",
                tip=tip,
                detail=exc.message,
                sleep_sec=delay,
            )
            await sleep(delay)
            delay = min(delay * 2, _STALL_RETRY_MAX_SEC)
            continue

        log_extra(
            logger,
            logging.INFO,
            "miner_block",
            mode="bootstrap",
            count=len(hashes),
            tip=activation,
            phase="activation",
        )
        return hashes


class Miner:
    """RPC-driven miner loop for testnet/regtest bootstrap and steady mining."""

    def __init__(
        self,
        settings: MinerSettings,
        rpc: RpcClient,
        *,
        stop_event: asyncio.Event | None = None,
        sleep: Any = asyncio.sleep,
    ) -> None:
        self._settings = settings
        self.rpc = rpc
        self._stop = stop_event or asyncio.Event()
        self._sleep = sleep
        self._mode: MinerMode | None = None
        self._address: str | None = None

    def request_stop(self) -> None:
        self._stop.set()

    async def bootstrap_wallet(self) -> str:
        await ensure_wallet(self.rpc, WALLET_NAME)
        # Switch client URL to wallet endpoint if still on root.
        if "/wallet/" not in self.rpc.url:
            wallet_url = wallet_rpc_url(self.rpc.url, WALLET_NAME)
            await self.rpc.aclose()
            self.rpc = RpcClient(
                wallet_url,
                self._settings.rpc_user,
                self._settings.rpc_password,
            )
        self._address = await resolve_mining_address(self.rpc)
        return self._address

    async def _with_rpc_retry(self, op_name: str, coro_factory: Any) -> Any:
        attempt = 0
        delay = _NODE_RETRY_INITIAL_SEC
        while True:
            if self._stop.is_set():
                raise asyncio.CancelledError()
            try:
                result = await coro_factory()
            except RpcHttpError as exc:
                if not is_rpc_connection_error(exc):
                    raise
                attempt += 1
                log_extra(
                    logger,
                    logging.WARNING,
                    "node_unreachable",
                    op=op_name,
                    attempt=attempt,
                    detail=exc.detail,
                    sleep_sec=delay,
                )
                await self._sleep(delay)
                delay = min(delay * 2, _NODE_RETRY_MAX_SEC)
                continue
            if attempt > 0:
                log_extra(
                    logger,
                    logging.INFO,
                    "node_recovered",
                    op=op_name,
                    attempts=attempt,
                )
            return result

    async def _blockchain_info(self) -> dict[str, Any]:
        info = await self._with_rpc_retry(
            "getblockchaininfo",
            lambda: self.rpc.call("getblockchaininfo"),
        )
        if not isinstance(info, dict):
            raise RuntimeError("getblockchaininfo returned non-dict")
        return info

    def _set_mode(self, mode: MinerMode) -> None:
        if self._mode != mode:
            log_extra(
                logger,
                logging.INFO,
                "miner_mode_change",
                from_mode=self._mode,
                to_mode=mode,
            )
            self._mode = mode

    async def tick_once(self) -> bool:
        """Run one mining decision. Returns False if stop was requested."""
        if self._stop.is_set():
            return False
        address = self._address
        if address is None:
            raise RuntimeError("bootstrap_wallet must run before tick_once")

        info = await self._blockchain_info()
        tip = int(info.get("blocks") or await self.rpc.call("getblockcount"))
        activation = predict_mweb_activation_height(info)

        if activation is None:
            self._set_mode("bootstrap")
            hashes = await self._with_rpc_retry(
                "generatetoaddress",
                lambda: mine_to(self.rpc, address, BOOTSTRAP_BATCH),
            )
            log_extra(
                logger,
                logging.INFO,
                "miner_block",
                mode="bootstrap",
                count=len(hashes),
                tip=tip + len(hashes),
                phase="await_activation_height",
            )
            await self._interruptible_sleep(self._settings.miner_bootstrap_sleep_sec)
            return not self._stop.is_set()

        mode = select_miner_mode(tip, activation)
        self._set_mode(mode)
        action = activation_boundary_action(tip, activation)

        if action == "steady":
            hashes = await self._with_rpc_retry(
                "generatetoaddress",
                lambda: mine_to(self.rpc, address, 1),
            )
            log_extra(
                logger,
                logging.INFO,
                "miner_block",
                mode="steady",
                count=len(hashes),
                tip=tip + len(hashes),
            )
            await self._interruptible_sleep(self._settings.miner_interval_sec)
            return not self._stop.is_set()

        if action == "activation_boundary":
            # Need mature coinbase before peg-in (tip should already be >> maturity
            # on testnet activation at 2880; still guard for short-period regtest).
            if tip < COINBASE_MATURITY + 1:
                n = min(BOOTSTRAP_BATCH, (COINBASE_MATURITY + 1) - tip)
                hashes = await self._with_rpc_retry(
                    "generatetoaddress",
                    lambda n=n: mine_to(self.rpc, address, n),
                )
                log_extra(
                    logger,
                    logging.INFO,
                    "miner_block",
                    mode="bootstrap",
                    count=len(hashes),
                    tip=tip + len(hashes),
                    phase="maturity",
                )
                await self._interruptible_sleep(self._settings.miner_bootstrap_sleep_sec)
                return not self._stop.is_set()

            await self._with_rpc_retry(
                "mine_activation",
                lambda: mine_activation_block(
                    self.rpc,
                    address,
                    activation,
                    sleep=self._sleep,
                ),
            )
            await self._interruptible_sleep(self._settings.miner_bootstrap_sleep_sec)
            return not self._stop.is_set()

        # approach or post_activation bootstrap mining
        if action == "approach":
            n = min(BOOTSTRAP_BATCH, (activation - 1) - tip)
        else:
            # post_activation but still in bootstrap window
            target = activation + COINBASE_MATURITY
            n = min(BOOTSTRAP_BATCH, target - tip)
        if n <= 0:
            await self._interruptible_sleep(self._settings.miner_bootstrap_sleep_sec)
            return not self._stop.is_set()

        hashes = await self._with_rpc_retry(
            "generatetoaddress",
            lambda n=n: mine_to(self.rpc, address, n),
        )
        log_extra(
            logger,
            logging.INFO,
            "miner_block",
            mode="bootstrap",
            count=len(hashes),
            tip=tip + len(hashes),
            phase=action,
        )
        await self._interruptible_sleep(self._settings.miner_bootstrap_sleep_sec)
        return not self._stop.is_set()

    async def _interruptible_sleep(self, seconds: float) -> None:
        if seconds <= 0:
            return
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=seconds)
        except TimeoutError:
            return

    async def run(self) -> None:
        await self.bootstrap_wallet()
        while not self._stop.is_set():
            try:
                cont = await self.tick_once()
            except asyncio.CancelledError:
                break
            if not cont:
                break


def _install_signal_handlers(loop: asyncio.AbstractEventLoop, stop: asyncio.Event) -> None:
    def _handler() -> None:
        stop.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _handler)
        except NotImplementedError:
            # Windows / limited loops: fall back to sync signal.
            signal.signal(sig, lambda *_: stop.set())


async def run_miner(settings: MinerSettings) -> None:
    """Entry point used by the CLI and tests."""
    if settings.network == "mainnet":
        msg = "explorer miner refuses to run on mainnet"
        raise SystemExit(msg)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    _install_signal_handlers(loop, stop)

    root = RpcClient(rpc_root_url(settings.rpc_url), settings.rpc_user, settings.rpc_password)
    miner = Miner(settings, root, stop_event=stop)
    try:
        await miner.run()
    finally:
        await miner.rpc.aclose()
