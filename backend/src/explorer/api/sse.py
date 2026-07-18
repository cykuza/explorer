"""Server-Sent Events stream for tip and mempool changes."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from explorer import tables
from explorer.api.context import NetworkContext
from explorer.api.deps import NetworkCtx, get_api_settings
from explorer.db import connect

router = APIRouter()

HEARTBEAT_SEC = 15.0

# Tests inspect this set to assert the stream coroutine is cleaned up on disconnect.
_active_stream_tasks: set[asyncio.Task[Any]] = set()


def _sse_event(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


def _sse_comment(text: str) -> str:
    return f": {text}\n\n"


async def _read_tip(ctx: NetworkContext) -> tuple[int, str, int] | None:
    async with connect(ctx.engine, ctx.schema) as conn:
        row = (
            await conn.execute(
                select(
                    tables.sync_state.c.height,
                    tables.sync_state.c.tip_hash,
                    tables.blocks.c.time,
                )
                .select_from(
                    tables.sync_state.join(
                        tables.blocks,
                        tables.sync_state.c.height == tables.blocks.c.height,
                    ),
                )
                .where(tables.sync_state.c.network == ctx.network),
            )
        ).one_or_none()
    if row is None:
        return None
    return int(row.height), str(row.tip_hash), int(row.time)


async def _read_mempool(ctx: NetworkContext) -> tuple[int, int] | None:
    try:
        info = await ctx.rpc.call("getmempoolinfo")
    except Exception:
        return None
    if not isinstance(info, dict):
        return None
    count = int(info.get("size") or 0)
    vsize = int(info.get("bytes") or info.get("vsize") or 0)
    return count, vsize


async def _event_stream(
    ctx: NetworkContext,
    poll_sec: float,
) -> AsyncIterator[str]:
    """Poll tip/mempool inline; cancelled when the ASGI client stops reading."""
    task = asyncio.current_task()
    if task is not None:
        _active_stream_tasks.add(task)

    last_tip: tuple[int, str] | None = None
    last_mempool: tuple[int, int] | None = None
    next_heartbeat = time.monotonic() + HEARTBEAT_SEC
    try:
        while True:
            tip = await _read_tip(ctx)
            if tip is not None:
                key = (tip[0], tip[1])
                if key != last_tip:
                    last_tip = key
                    yield _sse_event(
                        "tip",
                        {"height": tip[0], "hash": tip[1], "time": tip[2]},
                    )

            mempool = await _read_mempool(ctx)
            if mempool is not None and mempool != last_mempool:
                last_mempool = mempool
                yield _sse_event(
                    "mempool",
                    {"count": mempool[0], "vsize": mempool[1]},
                )

            now = time.monotonic()
            if now >= next_heartbeat:
                yield _sse_comment("heartbeat")
                next_heartbeat = now + HEARTBEAT_SEC

            await asyncio.sleep(poll_sec)
    finally:
        if task is not None:
            _active_stream_tasks.discard(task)


@router.get("/{network}/events")
async def network_events(
    request: Request,
    ctx: NetworkCtx,
) -> StreamingResponse:
    settings = get_api_settings(request)
    return StreamingResponse(
        _event_stream(ctx, settings.api_sse_poll_sec),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
