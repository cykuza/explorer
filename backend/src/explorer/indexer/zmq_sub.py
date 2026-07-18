"""Async ZMQ rawblock subscriber (notification trigger only)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

import zmq
import zmq.asyncio

from explorer.logging_setup import log_extra

logger = logging.getLogger(__name__)


async def rawblock_notifications(endpoint: str) -> AsyncIterator[None]:
    """Yield whenever a rawblock ZMQ message arrives (payload ignored)."""
    ctx = zmq.asyncio.Context.instance()
    socket = ctx.socket(zmq.SUB)
    socket.setsockopt(zmq.SUBSCRIBE, b"")
    socket.connect(endpoint)
    log_extra(logger, logging.INFO, "zmq_subscribed", endpoint=endpoint)
    try:
        while True:
            try:
                await socket.recv()
            except zmq.ZMQError as exc:
                log_extra(logger, logging.WARNING, "zmq_recv_error", error=str(exc))
                await asyncio.sleep(1)
                continue
            yield None
    finally:
        socket.close(linger=0)
