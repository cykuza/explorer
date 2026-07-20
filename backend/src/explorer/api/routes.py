"""Route handlers for API v1."""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import and_, func, or_, select, union
from sqlalchemy.ext.asyncio import AsyncConnection

from explorer import tables
from explorer.api.context import NetworkContext
from explorer.api.deps import NetworkCtx, get_api_settings, get_contexts
from explorer.api.downsample import downsample
from explorer.api.models import (
    AddressStatsResponse,
    AddressTxItem,
    AddressTxPage,
    BlockDetail,
    BlockSummary,
    BlockTxPage,
    ChartMetric,
    ChartPoint,
    HealthResponse,
    LatestTxItem,
    MempoolInfo,
    MempoolTxids,
    MempoolTxItem,
    MwebBlockInfo,
    MwebSummary,
    NetworkHealth,
    SearchHit,
    TipResponse,
    TxDetail,
    TxSummary,
    TxVin,
    TxVinPrevout,
    TxVout,
)
from explorer.api.money import decimal_str
from explorer.api.mweb_flags import PEGIN_SCRIPT_TYPE, has_mweb_flag, has_mweb_from_raw
from explorer.api.problems import raise_problem
from explorer.api.search import classify_query
from explorer.api.settings import MWEB_ACTIVATION_HEIGHT, ApiSettings
from explorer.db import connect
from explorer.indexer.fees import ZERO
from explorer.rpc import RpcError

router = APIRouter()


def _as_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return ZERO
    return Decimal(str(value))


def _mweb_info(row: Any) -> MwebBlockInfo:
    return MwebBlockInfo(
        height=int(row.height),
        hash=str(row.hash),
        kernel_offset=row.kernel_offset,
        stealth_offset=row.stealth_offset,
        num_kernels=int(row.num_kernels),
        num_txos=int(row.num_txos),
        kernel_root=row.kernel_root,
        output_root=row.output_root,
        leaf_root=row.leaf_root,
        mweb_amount=decimal_str(_as_decimal(row.mweb_amount)),
        pegin=decimal_str(_as_decimal(row.pegin)),
        pegout=decimal_str(_as_decimal(row.pegout)),
        kernel_fees=decimal_str(_as_decimal(row.kernel_fees)),
        hogex_txid=row.hogex_txid,
    )


async def _pegin_txids(conn: AsyncConnection, txids: list[str]) -> set[str]:
    if not txids:
        return set()
    rows = (
        await conn.execute(
            select(tables.outputs.c.txid)
            .where(
                and_(
                    tables.outputs.c.txid.in_(txids),
                    tables.outputs.c.script_type == PEGIN_SCRIPT_TYPE,
                ),
            )
            .distinct(),
        )
    ).all()
    return {str(r.txid) for r in rows}


def _tx_summary(row: Any, pegin_txids: set[str]) -> TxSummary:
    txid = str(row.txid)
    is_hogex = bool(row.is_hogex)
    return TxSummary(
        txid=txid,
        idx=int(row.idx),
        fee=decimal_str(_as_decimal(row.fee)),
        size=int(row.size) if row.size is not None else None,
        total_out=decimal_str(_as_decimal(row.total_out)),
        is_hogex=is_hogex,
        has_mweb=has_mweb_flag(is_hogex=is_hogex, has_pegin=txid in pegin_txids),
    )


async def _sync_tip(ctx: NetworkContext) -> tuple[int, str]:
    async with connect(ctx.engine, ctx.schema) as conn:
        row = (
            await conn.execute(
                select(tables.sync_state.c.height, tables.sync_state.c.tip_hash).where(
                    tables.sync_state.c.network == ctx.network,
                ),
            )
        ).one_or_none()
    if row is None:
        raise_problem(404, "Not Found", f"No sync state for network {ctx.network}")
    return int(row.height), str(row.tip_hash)


async def _resolve_block_id(ctx: NetworkContext, block_id: str) -> Any:
    async with connect(ctx.engine, ctx.schema) as conn:
        if block_id.isdigit():
            row = (
                await conn.execute(
                    select(tables.blocks).where(tables.blocks.c.height == int(block_id)),
                )
            ).one_or_none()
        elif len(block_id) == 64 and all(c in "0123456789abcdefABCDEF" for c in block_id):
            row = (
                await conn.execute(
                    select(tables.blocks).where(tables.blocks.c.hash == block_id.lower()),
                )
            ).one_or_none()
            if row is None:
                row = (
                    await conn.execute(
                        select(tables.blocks).where(tables.blocks.c.hash == block_id),
                    )
                ).one_or_none()
        else:
            raise_problem(404, "Not Found", f"Block not found: {block_id}")
    if row is None:
        raise_problem(404, "Not Found", f"Block not found: {block_id}")
    return row


@router.get("/{network}/tip", response_model=TipResponse, tags=["tip"])
async def get_tip(
    ctx: NetworkCtx,
) -> TipResponse:
    height, tip_hash = await _sync_tip(ctx)
    async with connect(ctx.engine, ctx.schema) as conn:
        block = (
            await conn.execute(
                select(tables.blocks.c.time).where(tables.blocks.c.height == height),
            )
        ).one_or_none()
    if block is None:
        raise_problem(404, "Not Found", f"Tip block missing at height {height}")
    return TipResponse(height=height, hash=tip_hash, time=int(block.time))


@router.get("/{network}/blocks", response_model=list[BlockSummary], tags=["blocks"])
async def list_blocks(
    ctx: NetworkCtx,
    before: int | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
) -> list[BlockSummary]:
    tip_height, _ = await _sync_tip(ctx)
    upper = before if before is not None else tip_height + 1
    async with connect(ctx.engine, ctx.schema) as conn:
        rows = (
            await conn.execute(
                select(
                    tables.blocks.c.height,
                    tables.blocks.c.hash,
                    tables.blocks.c.time,
                    tables.blocks.c.tx_count,
                    tables.blocks.c.size,
                    tables.blocks.c.total_out,
                    tables.blocks.c.fees,
                    tables.mweb_blocks.c.height.label("mweb_height"),
                )
                .select_from(
                    tables.blocks.outerjoin(
                        tables.mweb_blocks,
                        tables.blocks.c.height == tables.mweb_blocks.c.height,
                    ),
                )
                .where(tables.blocks.c.height < upper)
                .order_by(tables.blocks.c.height.desc())
                .limit(limit),
            )
        ).all()
    return [
        BlockSummary(
            height=int(r.height),
            hash=str(r.hash),
            time=int(r.time),
            tx_count=int(r.tx_count),
            size=int(r.size) if r.size is not None else None,
            total_out=decimal_str(_as_decimal(r.total_out)),
            fees=decimal_str(_as_decimal(r.fees)),
            has_mweb=r.mweb_height is not None,
        )
        for r in rows
    ]


@router.get("/{network}/txs", response_model=list[LatestTxItem], tags=["txs"])
async def list_latest_txs(
    ctx: NetworkCtx,
    limit: int = Query(default=12, ge=1, le=100),
) -> list[LatestTxItem]:
    async with connect(ctx.engine, ctx.schema) as conn:
        rows = (
            await conn.execute(
                select(
                    tables.txs.c.txid,
                    tables.txs.c.idx,
                    tables.txs.c.fee,
                    tables.txs.c.size,
                    tables.txs.c.total_out,
                    tables.txs.c.is_hogex,
                    tables.txs.c.block_height,
                    tables.blocks.c.time,
                )
                .select_from(
                    tables.txs.join(
                        tables.blocks,
                        tables.txs.c.block_height == tables.blocks.c.height,
                    ),
                )
                .order_by(tables.txs.c.block_height.desc(), tables.txs.c.idx.desc())
                .limit(limit),
            )
        ).all()
        pegin = await _pegin_txids(conn, [str(r.txid) for r in rows])
    return [
        LatestTxItem(
            **_tx_summary(r, pegin).model_dump(),
            block_height=int(r.block_height),
            time=int(r.time),
        )
        for r in rows
    ]


@router.get("/{network}/block/{block_id}", response_model=BlockDetail, tags=["block"])
async def get_block(
    block_id: str,
    ctx: NetworkCtx,
) -> BlockDetail:
    row = await _resolve_block_id(ctx, block_id)
    height = int(row.height)
    async with connect(ctx.engine, ctx.schema) as conn:
        mweb_row = (
            await conn.execute(
                select(tables.mweb_blocks).where(tables.mweb_blocks.c.height == height),
            )
        ).one_or_none()
        next_row = (
            await conn.execute(
                select(tables.blocks.c.hash).where(tables.blocks.c.height == height + 1),
            )
        ).one_or_none()
    difficulty = decimal_str(_as_decimal(row.difficulty)) if row.difficulty is not None else None
    return BlockDetail(
        height=height,
        hash=str(row.hash),
        prev_hash=str(row.prev_hash),
        next_hash=str(next_row.hash) if next_row is not None else None,
        time=int(row.time),
        version=int(row.version) if row.version is not None else None,
        bits=str(row.bits) if row.bits is not None else None,
        nonce=int(row.nonce) if row.nonce is not None else None,
        size=int(row.size) if row.size is not None else None,
        weight=int(row.weight) if row.weight is not None else None,
        difficulty=difficulty,
        tx_count=int(row.tx_count),
        total_out=decimal_str(_as_decimal(row.total_out)),
        fees=decimal_str(_as_decimal(row.fees)),
        mweb=_mweb_info(mweb_row) if mweb_row is not None else None,
    )


@router.get(
    "/{network}/block/{block_id}/txs",
    response_model=BlockTxPage,
    tags=["block"],
)
async def get_block_txs(
    block_id: str,
    ctx: NetworkCtx,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=25, ge=1, le=100),
) -> BlockTxPage:
    block = await _resolve_block_id(ctx, block_id)
    height = int(block.height)
    offset = (page - 1) * per_page
    async with connect(ctx.engine, ctx.schema) as conn:
        total = int(
            (
                await conn.execute(
                    select(func.count())
                    .select_from(tables.txs)
                    .where(tables.txs.c.block_height == height),
                )
            ).scalar_one(),
        )
        rows = (
            await conn.execute(
                select(tables.txs)
                .where(tables.txs.c.block_height == height)
                .order_by(tables.txs.c.idx.asc())
                .offset(offset)
                .limit(per_page),
            )
        ).all()
        pegin = await _pegin_txids(conn, [str(r.txid) for r in rows])
    return BlockTxPage(
        total=total,
        page=page,
        per_page=per_page,
        txs=[_tx_summary(r, pegin) for r in rows],
    )


@router.get("/{network}/tx/{txid}", response_model=TxDetail, tags=["tx"])
async def get_tx(
    txid: str,
    ctx: NetworkCtx,
) -> TxDetail:
    try:
        raw = await ctx.rpc.call("getrawtransaction", txid, 1)
    except RpcError:
        raise_problem(404, "Not Found", f"Transaction not found: {txid}")
    if not isinstance(raw, dict):
        raise_problem(502, "Bad Gateway", "Unexpected getrawtransaction response")

    tip_height, _ = await _sync_tip(ctx)

    async with connect(ctx.engine, ctx.schema) as conn:
        db_tx = (
            await conn.execute(select(tables.txs).where(tables.txs.c.txid == txid))
        ).one_or_none()

        prevouts: dict[tuple[str, int], tuple[str | None, Decimal]] = {}
        clauses = []
        for vin in raw.get("vin", []):
            if isinstance(vin, dict) and "txid" in vin and "vout" in vin:
                clauses.append(
                    and_(
                        tables.outputs.c.txid == str(vin["txid"]),
                        tables.outputs.c.n == int(vin["vout"]),
                    ),
                )
        if clauses:
            out_rows = (
                await conn.execute(
                    select(
                        tables.outputs.c.txid,
                        tables.outputs.c.n,
                        tables.outputs.c.address,
                        tables.outputs.c.value,
                    ).where(or_(*clauses)),
                )
            ).all()
            for o in out_rows:
                prevouts[(str(o.txid), int(o.n))] = (
                    str(o.address) if o.address is not None else None,
                    _as_decimal(o.value),
                )

        spend_rows = (
            await conn.execute(
                select(
                    tables.outputs.c.n,
                    tables.outputs.c.spent_by_txid,
                ).where(tables.outputs.c.txid == txid),
            )
        ).all()
        spent_by: dict[int, str | None] = {
            int(r.n): str(r.spent_by_txid) if r.spent_by_txid is not None else None
            for r in spend_rows
        }

    vins: list[TxVin] = []
    for vin in raw.get("vin", []):
        if not isinstance(vin, dict):
            continue
        prevout_model: TxVinPrevout | None = None
        if "txid" in vin and "vout" in vin:
            key = (str(vin["txid"]), int(vin["vout"]))
            if key in prevouts:
                addr, val = prevouts[key]
                prevout_model = TxVinPrevout(address=addr, value=decimal_str(val))
        vins.append(
            TxVin(
                txid=str(vin["txid"]) if "txid" in vin else None,
                vout=int(vin["vout"]) if "vout" in vin else None,
                coinbase=str(vin["coinbase"]) if "coinbase" in vin else None,
                scriptSig=vin.get("scriptSig"),
                sequence=int(vin["sequence"]) if "sequence" in vin else None,
                txinwitness=vin.get("txinwitness"),
                ismweb=bool(vin["ismweb"]) if "ismweb" in vin else None,
                prevout=prevout_model,
            ),
        )

    vouts: list[TxVout] = []
    for vout in raw.get("vout", []):
        if not isinstance(vout, dict):
            continue
        n = int(vout.get("n", 0))
        value_raw = vout.get("value")
        vouts.append(
            TxVout(
                n=n,
                value=decimal_str(_as_decimal(value_raw)) if value_raw is not None else None,
                scriptPubKey=vout.get("scriptPubKey"),
                ismweb=bool(vout["ismweb"]) if "ismweb" in vout else None,
                spent_by_txid=spent_by.get(n),
            ),
        )

    block_height = int(db_tx.block_height) if db_tx is not None else None
    confirmations = tip_height - block_height + 1 if block_height is not None else 0
    is_hogex = bool(db_tx.is_hogex) if db_tx is not None else False

    return TxDetail(
        txid=str(raw.get("txid", txid)),
        hash=str(raw["hash"]) if "hash" in raw else None,
        version=int(raw["version"]) if "version" in raw else None,
        size=int(raw["size"]) if "size" in raw else None,
        vsize=int(raw["vsize"]) if "vsize" in raw else None,
        weight=int(raw["weight"]) if "weight" in raw else None,
        locktime=int(raw["locktime"]) if "locktime" in raw else None,
        vin=vins,
        vout=vouts,
        hex=str(raw["hex"]) if "hex" in raw else None,
        blockhash=str(raw["blockhash"]) if "blockhash" in raw else None,
        block_height=block_height,
        idx=int(db_tx.idx) if db_tx is not None else None,
        fee=decimal_str(_as_decimal(db_tx.fee)) if db_tx is not None else None,
        is_hogex=is_hogex if db_tx is not None else None,
        has_mweb=has_mweb_from_raw(raw, is_hogex=is_hogex),
        confirmations=confirmations,
        time=int(raw["time"]) if "time" in raw else None,
        blocktime=int(raw["blocktime"]) if "blocktime" in raw else None,
    )


@router.get(
    "/{network}/address/{addr}",
    response_model=AddressStatsResponse,
    tags=["address"],
)
async def get_address(
    addr: str,
    ctx: NetworkCtx,
) -> AddressStatsResponse:
    async with connect(ctx.engine, ctx.schema) as conn:
        row = (
            await conn.execute(
                select(tables.address_stats).where(tables.address_stats.c.address == addr),
            )
        ).one_or_none()
    if row is None:
        raise_problem(404, "Not Found", f"Address not found: {addr}")
    return AddressStatsResponse(
        address=str(row.address),
        balance=decimal_str(_as_decimal(row.balance)),
        received=decimal_str(_as_decimal(row.received)),
        sent=decimal_str(_as_decimal(row.sent)),
        tx_count=int(row.tx_count),
        first_seen_height=int(row.first_seen_height),
        last_seen_height=int(row.last_seen_height),
    )


@router.get(
    "/{network}/address/{addr}/txs",
    response_model=AddressTxPage,
    tags=["address"],
)
async def get_address_txs(
    addr: str,
    ctx: NetworkCtx,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=25, ge=1, le=100),
) -> AddressTxPage:
    async with connect(ctx.engine, ctx.schema) as conn:
        stats = (
            await conn.execute(
                select(tables.address_stats.c.address).where(
                    tables.address_stats.c.address == addr,
                ),
            )
        ).one_or_none()
        if stats is None:
            raise_problem(404, "Not Found", f"Address not found: {addr}")

        created = select(
            tables.outputs.c.txid.label("txid"),
            tables.outputs.c.block_height.label("block_height"),
        ).where(tables.outputs.c.address == addr)
        spent = select(
            tables.outputs.c.spent_by_txid.label("txid"),
            tables.outputs.c.spent_at_height.label("block_height"),
        ).where(
            and_(
                tables.outputs.c.address == addr,
                tables.outputs.c.spent_by_txid.is_not(None),
            ),
        )
        combined = union(created, spent).subquery("addr_txs")
        total = int(
            (
                await conn.execute(
                    select(func.count()).select_from(
                        select(combined.c.txid).distinct().subquery(),
                    ),
                )
            ).scalar_one(),
        )

        # Distinct txids with max height, newest first
        ranked = (
            select(
                combined.c.txid,
                func.max(combined.c.block_height).label("block_height"),
            )
            .group_by(combined.c.txid)
            .subquery("ranked")
        )
        offset = (page - 1) * per_page
        page_rows = (
            await conn.execute(
                select(ranked.c.txid, ranked.c.block_height)
                .order_by(ranked.c.block_height.desc(), ranked.c.txid.desc())
                .offset(offset)
                .limit(per_page),
            )
        ).all()

        items: list[AddressTxItem] = []
        for pr in page_rows:
            txid = str(pr.txid)
            height = int(pr.block_height)
            received = _as_decimal(
                (
                    await conn.execute(
                        select(func.coalesce(func.sum(tables.outputs.c.value), 0)).where(
                            and_(
                                tables.outputs.c.txid == txid,
                                tables.outputs.c.address == addr,
                            ),
                        ),
                    )
                ).scalar_one(),
            )
            spent_amt = _as_decimal(
                (
                    await conn.execute(
                        select(func.coalesce(func.sum(tables.outputs.c.value), 0)).where(
                            and_(
                                tables.outputs.c.spent_by_txid == txid,
                                tables.outputs.c.address == addr,
                            ),
                        ),
                    )
                ).scalar_one(),
            )
            block_time = (
                await conn.execute(
                    select(tables.blocks.c.time).where(tables.blocks.c.height == height),
                )
            ).one_or_none()
            tx_row = (
                await conn.execute(
                    select(tables.txs.c.is_hogex).where(tables.txs.c.txid == txid),
                )
            ).one_or_none()
            is_hogex = bool(tx_row.is_hogex) if tx_row is not None else False
            has_pegin = (
                await conn.execute(
                    select(tables.outputs.c.txid)
                    .where(
                        and_(
                            tables.outputs.c.txid == txid,
                            tables.outputs.c.script_type == PEGIN_SCRIPT_TYPE,
                        ),
                    )
                    .limit(1),
                )
            ).one_or_none() is not None
            items.append(
                AddressTxItem(
                    txid=txid,
                    block_height=height,
                    time=int(block_time.time) if block_time is not None else 0,
                    delta=decimal_str(received - spent_amt),
                    is_hogex=is_hogex,
                    has_mweb=has_mweb_flag(is_hogex=is_hogex, has_pegin=has_pegin),
                ),
            )

    return AddressTxPage(total=total, page=page, per_page=per_page, txs=items)


@router.get("/{network}/mempool", response_model=MempoolInfo, tags=["mempool"])
async def get_mempool(
    ctx: NetworkCtx,
) -> MempoolInfo:
    info = await ctx.rpc.call("getmempoolinfo")
    if not isinstance(info, dict):
        raise_problem(502, "Bad Gateway", "Unexpected getmempoolinfo response")
    fee_raw = info.get("total_fee", info.get("fees", ZERO))
    if isinstance(fee_raw, dict):
        fee_raw = fee_raw.get("base", ZERO)
    return MempoolInfo(
        count=int(info.get("size") or 0),
        vsize=int(info.get("bytes") or info.get("vsize") or 0),
        total_fee=decimal_str(_as_decimal(fee_raw)),
    )


@router.get("/{network}/mempool/txs", response_model=MempoolTxids, tags=["mempool"])
async def get_mempool_txs(
    ctx: NetworkCtx,
    limit: int = Query(default=50, ge=1, le=1000),
) -> MempoolTxids:
    raw = await ctx.rpc.call("getrawmempool")
    if not isinstance(raw, list):
        raise_problem(502, "Bad Gateway", "Unexpected getrawmempool response")
    txids = [str(t) for t in raw[:limit]]
    items: list[MempoolTxItem] = []
    for txid in txids:
        has_mweb = False
        try:
            tx_raw = await ctx.rpc.call("getrawtransaction", txid, 1)
        except RpcError:
            tx_raw = None
        if isinstance(tx_raw, dict):
            has_mweb = has_mweb_from_raw(tx_raw, is_hogex=False)
        items.append(MempoolTxItem(txid=txid, has_mweb=has_mweb, is_hogex=False))
    return MempoolTxids(txids=txids, txs=items)


@router.get("/{network}/mweb/summary", response_model=MwebSummary, tags=["mweb"])
async def get_mweb_summary(
    ctx: NetworkCtx,
) -> MwebSummary:
    activation = MWEB_ACTIVATION_HEIGHT[ctx.network]
    cutoff = int(time.time()) - 86400
    async with connect(ctx.engine, ctx.schema) as conn:
        latest = (
            await conn.execute(
                select(tables.mweb_blocks).order_by(tables.mweb_blocks.c.height.desc()).limit(1),
            )
        ).one_or_none()
        peg_rows = (
            await conn.execute(
                select(
                    func.coalesce(func.sum(tables.mweb_blocks.c.pegin), 0),
                    func.coalesce(func.sum(tables.mweb_blocks.c.pegout), 0),
                )
                .select_from(
                    tables.mweb_blocks.join(
                        tables.blocks,
                        tables.mweb_blocks.c.height == tables.blocks.c.height,
                    ),
                )
                .where(tables.blocks.c.time >= cutoff),
            )
        ).one()
    mweb_amount = (
        decimal_str(_as_decimal(latest.mweb_amount)) if latest is not None else decimal_str(ZERO)
    )
    return MwebSummary(
        mweb_amount=mweb_amount,
        activation_height=activation,
        latest=_mweb_info(latest) if latest is not None else None,
        pegin_24h=decimal_str(_as_decimal(peg_rows[0])),
        pegout_24h=decimal_str(_as_decimal(peg_rows[1])),
    )


@router.get("/{network}/stats/charts", response_model=list[ChartPoint], tags=["stats"])
async def get_charts(
    ctx: NetworkCtx,
    metric: Annotated[ChartMetric, Query()],
    from_height: Annotated[int, Query(alias="from", ge=0)],
    to_height: Annotated[int, Query(alias="to", ge=0)],
) -> list[ChartPoint]:
    if to_height < from_height:
        raise_problem(422, "Unprocessable Entity", "'to' must be >= 'from'")

    async with connect(ctx.engine, ctx.schema) as conn:
        if metric == "mweb_amount":
            rows = (
                await conn.execute(
                    select(
                        tables.mweb_blocks.c.height,
                        tables.blocks.c.time,
                        tables.mweb_blocks.c.mweb_amount,
                    )
                    .select_from(
                        tables.mweb_blocks.join(
                            tables.blocks,
                            tables.mweb_blocks.c.height == tables.blocks.c.height,
                        ),
                    )
                    .where(
                        and_(
                            tables.mweb_blocks.c.height >= from_height,
                            tables.mweb_blocks.c.height <= to_height,
                        ),
                    )
                    .order_by(tables.mweb_blocks.c.height.asc()),
                )
            ).all()
            series = [(int(r.height), int(r.time), _as_decimal(r.mweb_amount)) for r in rows]
            agg: Literal["avg", "sum", "last"] = "last"
        else:
            col = {
                "difficulty": tables.blocks.c.difficulty,
                "tx_count": tables.blocks.c.tx_count,
                "fees": tables.blocks.c.fees,
            }[metric]
            rows = (
                await conn.execute(
                    select(tables.blocks.c.height, tables.blocks.c.time, col)
                    .where(
                        and_(
                            tables.blocks.c.height >= from_height,
                            tables.blocks.c.height <= to_height,
                        ),
                    )
                    .order_by(tables.blocks.c.height.asc()),
                )
            ).all()
            series = [(int(r.height), int(r.time), _as_decimal(r[2])) for r in rows]
            agg = "avg" if metric == "difficulty" else "sum"

    down = downsample(series, agg=agg, max_points=500)
    if metric in ("difficulty", "fees", "mweb_amount"):
        return [ChartPoint(height=h, time=t, value=decimal_str(v)) for h, t, v in down]
    return [ChartPoint(height=h, time=t, value=str(int(v))) for h, t, v in down]


@router.get("/{network}/search/{q}", response_model=SearchHit, tags=["search"])
async def search(
    q: str,
    ctx: NetworkCtx,
) -> SearchHit:
    tip_height, _ = await _sync_tip(ctx)
    kind = classify_query(q, tip_height)
    if kind is None:
        raise_problem(404, "Not Found", f"No match for: {q}")

    async with connect(ctx.engine, ctx.schema) as conn:
        if kind == "block_height":
            height = int(q)
            row = (
                await conn.execute(
                    select(tables.blocks.c.height).where(tables.blocks.c.height == height),
                )
            ).one_or_none()
            if row is None:
                raise_problem(404, "Not Found", f"No match for: {q}")
            return SearchHit(type="block", id=str(height))

        if kind == "hex64":
            block = (
                await conn.execute(
                    select(tables.blocks.c.hash).where(
                        tables.blocks.c.hash == q.lower(),
                    ),
                )
            ).one_or_none()
            if block is None:
                block = (
                    await conn.execute(
                        select(tables.blocks.c.hash).where(tables.blocks.c.hash == q),
                    )
                ).one_or_none()
            if block is not None:
                return SearchHit(type="block", id=str(block.hash))
            tx = (
                await conn.execute(
                    select(tables.txs.c.txid).where(tables.txs.c.txid == q.lower()),
                )
            ).one_or_none()
            if tx is None:
                tx = (
                    await conn.execute(
                        select(tables.txs.c.txid).where(tables.txs.c.txid == q),
                    )
                ).one_or_none()
            if tx is not None:
                return SearchHit(type="tx", id=str(tx.txid))
            raise_problem(404, "Not Found", f"No match for: {q}")

        # address
        addr = (
            await conn.execute(
                select(tables.address_stats.c.address).where(
                    tables.address_stats.c.address == q,
                ),
            )
        ).one_or_none()
        if addr is None:
            raise_problem(404, "Not Found", f"No match for: {q}")
        return SearchHit(type="address", id=str(addr.address))


health_router = APIRouter()


@health_router.get("/healthz", response_model=HealthResponse, tags=["health"])
async def healthz(request: Request) -> HealthResponse | JSONResponse:
    settings: ApiSettings = get_api_settings(request)
    contexts = get_contexts(request)
    networks: dict[str, NetworkHealth] = {}
    unhealthy = False
    for network, ctx in contexts.items():
        async with connect(ctx.engine, ctx.schema) as conn:
            row = (
                await conn.execute(
                    select(tables.sync_state.c.height).where(
                        tables.sync_state.c.network == network,
                    ),
                )
            ).one_or_none()
        db_height = int(row.height) if row is not None else -1
        try:
            info = await ctx.rpc.call("getblockchaininfo")
            node_height = int(info["blocks"])
            node_headers = int(info["headers"])
            ibd = bool(info["initialblockdownload"])
            lag = max(node_height - db_height, 0) if db_height >= 0 else settings.api_max_lag + 1
        except Exception:
            node_height = -1
            node_headers = -1
            ibd = True
            lag = settings.api_max_lag + 1
        if lag > settings.api_max_lag or ibd:
            unhealthy = True
        networks[network] = NetworkHealth(
            db_height=db_height,
            node_height=node_height,
            node_headers=node_headers,
            ibd=ibd,
            lag=lag,
        )
    body = HealthResponse(networks=networks)
    if unhealthy:
        return JSONResponse(status_code=503, content=body.model_dump())
    return body
