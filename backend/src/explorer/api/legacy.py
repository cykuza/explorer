"""Legacy `/api/*` adapters for cyberyen.work consumers (default network)."""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text

from explorer import tables
from explorer.api.context import NetworkContext
from explorer.api.deps import DefaultNetworkCtx
from explorer.api.money import decimal_str
from explorer.db import connect
from explorer.indexer.fees import ZERO
from explorer.rpc import RpcError

router = APIRouter()

_CACHE_TTL_SEC = 60.0
_cache: dict[str, tuple[float, str]] = {}

StatField = Literal["balance", "received", "sent"]


def _ok(message: str) -> JSONResponse:
    return JSONResponse({"error": "ok", "message": message}, status_code=200)


def _err_404(message: str = "There was a JSON error. Try again later") -> JSONResponse:
    return JSONResponse({"error": "404", "message": message}, status_code=200)


def _err_invalid_addr() -> JSONResponse:
    return JSONResponse(
        {"error": "404", "message": "This address is invalid"},
        status_code=200,
    )


def _err_invalid_tx() -> JSONResponse:
    return JSONResponse(
        {"error": "invalid", "message": "This transaction is invalid"},
        status_code=200,
    )


def _err_validate_failed() -> JSONResponse:
    return JSONResponse(
        {
            "error": "this string cannot be verified as an address",
            "message": "invalid",
        },
        status_code=200,
    )


def _as_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return ZERO
    return Decimal(str(value))


async def _rpc_address_valid(ctx: NetworkContext, addr: str) -> bool:
    try:
        result = await ctx.rpc.call("validateaddress", addr)
    except RpcError:
        return False
    if not isinstance(result, dict):
        return False
    return bool(result.get("isvalid"))


async def _address_stat(
    ctx: NetworkContext,
    addr: str,
    field: StatField,
) -> JSONResponse:
    async with connect(ctx.engine, ctx.schema) as conn:
        row = (
            await conn.execute(
                select(tables.address_stats).where(
                    tables.address_stats.c.address == addr,
                ),
            )
        ).one_or_none()
    if row is not None:
        return _ok(decimal_str(_as_decimal(getattr(row, field))))
    if await _rpc_address_valid(ctx, addr):
        return _ok(decimal_str(ZERO))
    return _err_invalid_addr()


async def _sync_tip(ctx: NetworkContext) -> tuple[int, str] | None:
    async with connect(ctx.engine, ctx.schema) as conn:
        row = (
            await conn.execute(
                select(tables.sync_state.c.height, tables.sync_state.c.tip_hash).where(
                    tables.sync_state.c.network == ctx.network,
                ),
            )
        ).one_or_none()
    if row is None:
        return None
    return int(row.height), str(row.tip_hash)


def _cache_get(key: str) -> str | None:
    hit = _cache.get(key)
    if hit is None:
        return None
    ts, value = hit
    if time.monotonic() - ts >= _CACHE_TTL_SEC:
        return None
    return value


def _cache_set(key: str, value: str) -> None:
    _cache[key] = (time.monotonic(), value)


async def _circulating_supply(ctx: NetworkContext) -> str:
    cache_key = f"supply:{ctx.network}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    # Single aggregate: Σ coinbase total_out − Σ block fees
    async with connect(ctx.engine, ctx.schema) as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT COALESCE((SELECT SUM(total_out) FROM txs WHERE idx = 0), 0)"
                    " - COALESCE((SELECT SUM(fees) FROM blocks), 0) AS supply",
                ),
            )
        ).one()
    value = decimal_str(_as_decimal(row.supply))
    _cache_set(cache_key, value)
    return value


async def _total_transactions(ctx: NetworkContext) -> str:
    cache_key = f"txcount:{ctx.network}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    async with connect(ctx.engine, ctx.schema) as conn:
        count = (await conn.execute(select(func.count()).select_from(tables.txs))).scalar_one()
    value = str(int(count))
    _cache_set(cache_key, value)
    return value


@router.get("/addressbalance/{addr}", include_in_schema=False)
async def addressbalance(ctx: DefaultNetworkCtx, addr: str) -> JSONResponse:
    return await _address_stat(ctx, addr, "balance")


@router.get("/receivedbyaddress/{addr}", include_in_schema=False)
async def receivedbyaddress(ctx: DefaultNetworkCtx, addr: str) -> JSONResponse:
    return await _address_stat(ctx, addr, "received")


@router.get("/sentbyaddress/{addr}", include_in_schema=False)
async def sentbyaddress(ctx: DefaultNetworkCtx, addr: str) -> JSONResponse:
    return await _address_stat(ctx, addr, "sent")


@router.get("/validateaddress/{addr}", include_in_schema=False)
async def validateaddress(ctx: DefaultNetworkCtx, addr: str) -> JSONResponse:
    if await _rpc_address_valid(ctx, addr):
        return _ok("valid")
    return _err_validate_failed()


@router.get("/rawtx/{txid}", include_in_schema=False)
async def rawtx(ctx: DefaultNetworkCtx, txid: str) -> JSONResponse:
    try:
        raw = await ctx.rpc.call("getrawtransaction", txid, 1)
    except RpcError:
        return _err_invalid_tx()
    if not isinstance(raw, dict):
        return _err_invalid_tx()
    return JSONResponse(jsonable_encoder(raw), status_code=200)


@router.get("/block/getbestblockhash", include_in_schema=False)
async def getbestblockhash(ctx: DefaultNetworkCtx) -> JSONResponse:
    tip = await _sync_tip(ctx)
    if tip is None:
        return _err_404()
    return JSONResponse(tip[1], status_code=200)


@router.get("/block/getblockcount", include_in_schema=False)
async def getblockcount(ctx: DefaultNetworkCtx) -> JSONResponse:
    tip = await _sync_tip(ctx)
    if tip is None:
        return _err_404()
    return _ok(str(tip[0]))


@router.get("/block/{hash}", include_in_schema=False)
async def block_by_hash(ctx: DefaultNetworkCtx, hash: str) -> JSONResponse:
    try:
        raw = await ctx.rpc.call("getblock", hash, 2)
    except RpcError:
        return _err_invalid_tx()
    if not isinstance(raw, dict):
        return _err_invalid_tx()
    return JSONResponse(jsonable_encoder(raw), status_code=200)


@router.get("/getsummary", include_in_schema=False)
async def getsummary(ctx: DefaultNetworkCtx) -> JSONResponse:
    if await _sync_tip(ctx) is None:
        return _err_404()
    try:
        return _ok(await _circulating_supply(ctx))
    except Exception:
        return _err_404()


@router.get("/totaltransactions", include_in_schema=False)
async def totaltransactions(ctx: DefaultNetworkCtx) -> JSONResponse:
    if await _sync_tip(ctx) is None:
        return _err_404()
    try:
        return _ok(await _total_transactions(ctx))
    except Exception:
        return _err_404()


@router.get("/confirmations/{height}", include_in_schema=False)
async def confirmations(ctx: DefaultNetworkCtx, height: int) -> JSONResponse:
    tip = await _sync_tip(ctx)
    if tip is None:
        return _err_404()
    tip_height = tip[0]
    if height < 0 or height > tip_height:
        return _err_404()
    return _ok(str(tip_height - height + 1))


@router.get("/lastdifficulty", include_in_schema=False)
async def lastdifficulty(ctx: DefaultNetworkCtx) -> JSONResponse:
    tip = await _sync_tip(ctx)
    if tip is None:
        return _err_404()
    async with connect(ctx.engine, ctx.schema) as conn:
        row = (
            await conn.execute(
                select(tables.blocks.c.difficulty).where(
                    tables.blocks.c.height == tip[0],
                ),
            )
        ).one_or_none()
    if row is None or row.difficulty is None:
        return _err_404()
    return _ok(decimal_str(_as_decimal(row.difficulty)))


def clear_legacy_cache() -> None:
    """Test helper: drop in-process TTL caches."""
    _cache.clear()
