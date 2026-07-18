"""Indexer sync loop: RPC backfill, ZMQ triggers, poll fallback, reorg handling."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from explorer.config import Settings
from explorer.db import begin, connect, create_engine
from explorer.indexer.apply import (
    apply_block,
    get_block_hash,
    get_sync_height,
    rollback_block,
)
from explorer.indexer.reorg import ReorgTooDeepError, find_fork_height
from explorer.indexer.zmq_sub import rawblock_notifications
from explorer.logging_setup import log_extra
from explorer.rpc import RpcClient

logger = logging.getLogger(__name__)


class Syncer:
    """Orchestrates tip-walk sync against a Cyberyen node and Postgres index."""

    def __init__(
        self,
        settings: Settings,
        rpc: RpcClient,
        engine: AsyncEngine,
    ) -> None:
        self._settings = settings
        self._rpc = rpc
        self._engine = engine
        self._schema = settings.db_schema
        assert self._schema is not None
        self._lock = asyncio.Lock()
        self._wake = asyncio.Event()

    async def tip_walk_once(self) -> int:
        """Sync from DB height+1 to node tip. Returns number of blocks applied."""
        async with self._lock:
            return await self._tip_walk_locked()

    async def _tip_walk_locked(self) -> int:
        schema = self._schema
        assert schema is not None
        network = self._settings.network
        applied = 0

        while True:
            async with connect(self._engine, schema) as conn:
                db_height, db_tip_hash = await get_sync_height(conn, network)

            node_tip = int(await self._rpc.call("getblockcount"))

            # Detect reorg when DB is ahead of the node, or tip hash diverged.
            if db_height >= 0:
                if db_height > node_tip:
                    await self._rollback_to_height(node_tip)
                    continue
                node_hash_at_db = str(await self._rpc.call("getblockhash", db_height))
                if db_tip_hash is not None and node_hash_at_db != db_tip_hash:
                    await self._handle_reorg(db_height)
                    continue

            if db_height >= node_tip:
                return applied

            height = db_height + 1
            block_hash = str(await self._rpc.call("getblockhash", height))
            block: dict[str, Any] = await self._rpc.call("getblock", block_hash, 2)
            prev_hash = str(block.get("previousblockhash") or ("0" * 64))

            if height > 0:
                async with connect(self._engine, schema) as conn:
                    stored_prev = await get_block_hash(conn, height - 1)
                if stored_prev is not None and stored_prev != prev_hash:
                    await self._handle_reorg(db_height)
                    continue  # restart from new DB tip

            t0 = time.perf_counter()
            async with begin(self._engine, schema) as conn:
                await apply_block(conn, block, network=network)
            duration_ms = (time.perf_counter() - t0) * 1000
            log_extra(
                logger,
                logging.INFO,
                "block_applied",
                height=height,
                hash=block_hash,
                tx_count=len(block.get("tx") or []),
                duration_ms=round(duration_ms, 2),
            )
            applied += 1

    async def _rollback_to_height(self, target_height: int) -> None:
        """Roll back DB tip down to ``target_height`` (inclusive kept)."""
        schema = self._schema
        assert schema is not None
        network = self._settings.network
        async with connect(self._engine, schema) as conn:
            db_height, _ = await get_sync_height(conn, network)
        for h in range(db_height, target_height, -1):
            async with begin(self._engine, schema) as conn:
                await rollback_block(conn, h, network=network)
            log_extra(
                logger,
                logging.WARNING,
                "reorg_rollback",
                height=h,
                fork_height=target_height,
            )

    async def _handle_reorg(self, db_height: int) -> None:
        schema = self._schema
        assert schema is not None
        max_depth = self._settings.max_reorg_depth

        stored_hash_at: dict[int, str] = {}
        node_hash_at: dict[int, str] = {}
        for h in range(db_height, -1, -1):
            if db_height - h > max_depth:
                break
            async with connect(self._engine, schema) as conn:
                stored = await get_block_hash(conn, h)
            if stored is None:
                break
            stored_hash_at[h] = stored
            try:
                node_hash_at[h] = str(await self._rpc.call("getblockhash", h))
            except Exception:
                # Height absent on node — keep walking for a lower common ancestor.
                continue

        try:
            fork = find_fork_height(
                db_tip_height=db_height,
                stored_hash_at=stored_hash_at,
                node_hash_at=node_hash_at,
                max_reorg_depth=max_depth,
            )
        except ReorgTooDeepError:
            log_extra(
                logger,
                logging.ERROR,
                "reorg_too_deep",
                db_height=db_height,
                max_reorg_depth=max_depth,
            )
            raise

        log_extra(
            logger,
            logging.WARNING,
            "reorg_detected",
            fork_height=fork,
            db_height=db_height,
        )

        await self._rollback_to_height(fork)

    def request_sync(self) -> None:
        """Wake the sync loop (ZMQ or poll)."""
        self._wake.set()

    async def run(self, *, once: bool = False) -> None:
        """Run backfill then optionally stay on ZMQ+poll until cancelled.

        If ``once`` is True, only tip-walk to current tip and return (for tests).
        """
        applied = await self.tip_walk_once()
        log_extra(logger, logging.INFO, "backfill_done", blocks_applied=applied)
        if once:
            return

        self._wake.set()
        poll_task = asyncio.create_task(self._poll_loop(), name="sync-poll")
        zmq_task = asyncio.create_task(self._zmq_loop(), name="sync-zmq")
        try:
            while True:
                await self._wake.wait()
                self._wake.clear()
                try:
                    await self.tip_walk_once()
                except Exception:
                    logger.exception("tip_walk_failed")
        finally:
            poll_task.cancel()
            zmq_task.cancel()
            await asyncio.gather(poll_task, zmq_task, return_exceptions=True)

    async def _poll_loop(self) -> None:
        interval = self._settings.sync_poll_interval_sec
        while True:
            await asyncio.sleep(interval)
            self.request_sync()

    async def _zmq_loop(self) -> None:
        async for _ in rawblock_notifications(self._settings.zmq_rawblock):
            self.request_sync()


async def run_sync(settings: Settings, *, once: bool = False) -> None:
    """Entry point used by the CLI and integration tests."""
    engine = create_engine(settings)
    rpc = RpcClient(settings.rpc_url, settings.rpc_user, settings.rpc_password)
    syncer = Syncer(settings, rpc, engine)
    try:
        await syncer.run(once=once)
    finally:
        await rpc.aclose()
        await engine.dispose()
