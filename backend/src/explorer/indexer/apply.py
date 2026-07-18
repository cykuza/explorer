"""Apply and rollback a single block in one DB transaction."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncConnection

from explorer import tables
from explorer.indexer.addresses import (
    AddressDelta,
    apply_receive,
    apply_spend,
    extract_address,
    extract_script_type,
)
from explorer.indexer.fees import ZERO, compute_fee, sum_values


class IndexIntegrityError(Exception):
    """Raised when a required prevout is missing from the index."""


def _as_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        return Decimal(value)
    raise TypeError(f"cannot convert {type(value).__name__} to Decimal without float")


def _is_mweb(entry: dict[str, Any]) -> bool:
    return bool(entry.get("ismweb"))


def _is_coinbase(vin: list[dict[str, Any]]) -> bool:
    return bool(vin) and "coinbase" in vin[0]


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _sats_to_coins(value: Any) -> Decimal:
    """Convert an integer satoshi amount to coins (1e-8)."""
    return _as_decimal(value) / Decimal(100_000_000)


def _aggregate_vkern(
    raw_txs: list[dict[str, Any]],
) -> tuple[Decimal, Decimal, Decimal] | None:
    """Sum pegin/pegout/fees from txs' vkern arrays.

    Returns None if no tx carries a vkern array (older/newer RPC shapes).
    """
    found = False
    pegin = ZERO
    pegout = ZERO
    kernel_fees = ZERO
    for tx in raw_txs:
        vkern = tx.get("vkern") or []
        if not isinstance(vkern, list) or not vkern:
            continue
        found = True
        for kernel in vkern:
            if not isinstance(kernel, dict):
                continue
            if "pegin" in kernel and kernel["pegin"] is not None:
                pegin += _as_decimal(kernel["pegin"])
            if "fee" in kernel and kernel["fee"] is not None:
                kernel_fees += _as_decimal(kernel["fee"])
            pegouts = kernel.get("pegout") or []
            if not isinstance(pegouts, list):
                continue
            for entry in pegouts:
                if not isinstance(entry, dict):
                    continue
                if "value" in entry and entry["value"] is not None:
                    pegout += _as_decimal(entry["value"])
    if not found:
        return None
    return pegin, pegout, kernel_fees


def _aggregate_mweb_fallback(
    block: dict[str, Any],
    raw_txs: list[dict[str, Any]],
    mweb_section: dict[str, Any],
) -> tuple[Decimal, Decimal, Decimal]:
    """Derive peg aggregates when txs lack vkern (Cyberyen getblock shape).

    - pegin: sum of ``witness_mweb_pegin`` output values
    - pegout: sum of HogEx vouts after vout[0] (peg-out payments)
    - kernel_fees: sum of ``mweb.kernels[].fee`` (integer satoshis)
    """
    pegin = ZERO
    for tx in raw_txs:
        for vout in tx.get("vout") or []:
            if not isinstance(vout, dict):
                continue
            spk = vout.get("scriptPubKey") or {}
            if not isinstance(spk, dict):
                continue
            if spk.get("type") == "witness_mweb_pegin":
                pegin += _as_decimal(vout.get("value", ZERO))

    pegout = ZERO
    if raw_txs:
        hogex = raw_txs[-1]
        vouts = list(hogex.get("vout") or [])
        for vout in vouts[1:]:
            if not isinstance(vout, dict):
                continue
            if vout.get("ismweb"):
                continue
            pegout += _as_decimal(vout.get("value", ZERO))

    kernel_fees = ZERO
    kernels = mweb_section.get("kernels") or []
    if isinstance(kernels, list):
        for kernel in kernels:
            if isinstance(kernel, dict) and kernel.get("fee") is not None:
                kernel_fees += _sats_to_coins(kernel["fee"])

    return pegin, pegout, kernel_fees


def _mweb_amount_from_block(
    block: dict[str, Any],
    raw_txs: list[dict[str, Any]],
) -> Decimal:
    """Total coins pegged into MWEB as of this block (HogEx vout[0])."""
    raw = block.get("mweb_amount")
    if raw is not None:
        return _as_decimal(raw)
    if raw_txs:
        hogex_vouts = list(raw_txs[-1].get("vout") or [])
        if hogex_vouts and isinstance(hogex_vouts[0], dict):
            return _as_decimal(hogex_vouts[0].get("value", ZERO))
    return ZERO


async def get_sync_height(conn: AsyncConnection, network: str) -> tuple[int, str | None]:
    """Return ``(height, tip_hash)``; height ``-1`` if no sync_state row."""
    row = (
        await conn.execute(
            select(tables.sync_state.c.height, tables.sync_state.c.tip_hash).where(
                tables.sync_state.c.network == network,
            ),
        )
    ).one_or_none()
    if row is None:
        return -1, None
    return int(row.height), str(row.tip_hash)


async def get_block_hash(conn: AsyncConnection, height: int) -> str | None:
    """Return stored block hash at height, or None."""
    row = (
        await conn.execute(
            select(tables.blocks.c.hash).where(tables.blocks.c.height == height),
        )
    ).one_or_none()
    return str(row.hash) if row is not None else None


async def _load_prevouts(
    conn: AsyncConnection,
    keys: list[tuple[str, int]],
) -> dict[tuple[str, int], tuple[Decimal, str | None]]:
    """Load ``(value, address)`` for prevout keys from outputs."""
    if not keys:
        return {}
    txids = sorted({txid for txid, _n in keys})
    rows = (
        await conn.execute(
            select(
                tables.outputs.c.txid,
                tables.outputs.c.n,
                tables.outputs.c.value,
                tables.outputs.c.address,
            ).where(tables.outputs.c.txid.in_(txids)),
        )
    ).all()
    wanted = set(keys)
    result: dict[tuple[str, int], tuple[Decimal, str | None]] = {}
    for row in rows:
        key = (str(row.txid), int(row.n))
        if key in wanted:
            result[key] = (_as_decimal(row.value), row.address)
    return result


async def _last_seen_height_before(
    conn: AsyncConnection,
    address: str,
    *,
    before_height: int,
) -> int | None:
    """Max activity height for address strictly below ``before_height``."""
    created = (
        await conn.execute(
            select(func.max(tables.outputs.c.block_height)).where(
                tables.outputs.c.address == address,
                tables.outputs.c.block_height < before_height,
            ),
        )
    ).scalar_one()
    spent = (
        await conn.execute(
            select(func.max(tables.outputs.c.spent_at_height)).where(
                tables.outputs.c.address == address,
                tables.outputs.c.spent_at_height.is_not(None),
                tables.outputs.c.spent_at_height < before_height,
            ),
        )
    ).scalar_one()
    heights = [int(h) for h in (created, spent) if h is not None]
    if not heights:
        return None
    return max(heights)


async def _upsert_address_stats(
    conn: AsyncConnection,
    deltas: dict[str, AddressDelta],
    *,
    height: int,
    reverse: bool = False,
) -> None:
    """Apply address_stats deltas (or reverse them on rollback)."""
    for address, delta in deltas.items():
        received = -delta.received if reverse else delta.received
        sent = -delta.sent if reverse else delta.sent
        balance = received - sent
        tx_count = -delta.tx_count if reverse else delta.tx_count

        if reverse:
            existing = (
                await conn.execute(
                    select(tables.address_stats).where(
                        tables.address_stats.c.address == address,
                    ),
                )
            ).one_or_none()
            if existing is None:
                continue
            new_received = _as_decimal(existing.received) + received
            new_sent = _as_decimal(existing.sent) + sent
            new_balance = _as_decimal(existing.balance) + balance
            new_tx_count = max(0, int(existing.tx_count) + tx_count)
            if (
                new_received == ZERO
                and new_sent == ZERO
                and new_balance == ZERO
                and new_tx_count == 0
            ):
                await conn.execute(
                    tables.address_stats.delete().where(
                        tables.address_stats.c.address == address,
                    ),
                )
            else:
                last_seen = await _last_seen_height_before(
                    conn,
                    address,
                    before_height=height,
                )
                if last_seen is None:
                    last_seen = int(existing.first_seen_height)
                await conn.execute(
                    update(tables.address_stats)
                    .where(tables.address_stats.c.address == address)
                    .values(
                        received=new_received,
                        sent=new_sent,
                        balance=new_balance,
                        tx_count=new_tx_count,
                        last_seen_height=last_seen,
                    ),
                )
            continue

        stmt = pg_insert(tables.address_stats).values(
            address=address,
            balance=balance,
            received=received,
            sent=sent,
            tx_count=tx_count,
            first_seen_height=height,
            last_seen_height=height,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[tables.address_stats.c.address],
            set_={
                "balance": tables.address_stats.c.balance + stmt.excluded.balance,
                "received": tables.address_stats.c.received + stmt.excluded.received,
                "sent": tables.address_stats.c.sent + stmt.excluded.sent,
                "tx_count": tables.address_stats.c.tx_count + stmt.excluded.tx_count,
                "last_seen_height": stmt.excluded.last_seen_height,
            },
        )
        await conn.execute(stmt)


async def _upsert_sync_state(
    conn: AsyncConnection,
    *,
    network: str,
    height: int,
    tip_hash: str,
) -> None:
    stmt = pg_insert(tables.sync_state).values(
        network=network,
        height=height,
        tip_hash=tip_hash,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[tables.sync_state.c.network],
        set_={
            "height": stmt.excluded.height,
            "tip_hash": stmt.excluded.tip_hash,
            "updated_at": func.now(),
        },
    )
    await conn.execute(stmt)


async def apply_block(
    conn: AsyncConnection,
    block: dict[str, Any],
    *,
    network: str,
) -> None:
    """Index one block (verbosity=2) inside the caller's transaction."""
    height = int(block["height"])
    block_hash = str(block["hash"])
    prev_hash = str(block.get("previousblockhash") or ("0" * 64))

    if height > 0:
        stored_prev = await get_block_hash(conn, height - 1)
        if stored_prev is None or stored_prev != prev_hash:
            raise IndexIntegrityError(
                f"prev_hash mismatch at height {height}: "
                f"block.prev={prev_hash} stored={stored_prev}",
            )

    raw_txs: list[dict[str, Any]] = list(block.get("tx") or [])
    prevout_keys: list[tuple[str, int]] = []
    for tx in raw_txs:
        vins: list[dict[str, Any]] = list(tx.get("vin") or [])
        if _is_coinbase(vins):
            continue
        for vin in vins:
            if _is_mweb(vin):
                continue
            txid = vin.get("txid")
            vout = vin.get("vout")
            if not isinstance(txid, str) or not isinstance(vout, int):
                continue
            prevout_keys.append((txid, vout))

    prevouts = await _load_prevouts(conn, prevout_keys)

    deltas: dict[str, AddressDelta] = {}
    tx_rows: list[dict[str, Any]] = []
    output_rows: list[dict[str, Any]] = []
    spend_updates: list[tuple[str, int, str, int]] = []

    block_total_out = ZERO
    block_fees = ZERO
    mweb_section = block.get("mweb")
    has_mweb = isinstance(mweb_section, dict)
    hogex_txid: str | None = None
    if has_mweb and raw_txs:
        hogex_txid = str(raw_txs[-1]["txid"])

    for idx, tx in enumerate(raw_txs):
        txid = str(tx["txid"])
        vins = list(tx.get("vin") or [])
        vouts = list(tx.get("vout") or [])
        is_coinbase = _is_coinbase(vins)
        is_hogex = has_mweb and hogex_txid is not None and txid == hogex_txid

        out_values: list[Decimal] = []
        for vout_idx, vout in enumerate(vouts):
            if _is_mweb(vout):
                continue
            value = _as_decimal(vout.get("value", ZERO))
            out_values.append(value)
            spk = vout.get("scriptPubKey") or {}
            if not isinstance(spk, dict):
                spk = {}
            address = extract_address(spk)
            script_type = extract_script_type(spk)
            n = int(vout["n"]) if "n" in vout else vout_idx
            output_rows.append(
                {
                    "txid": txid,
                    "n": n,
                    "block_height": height,
                    "value": value,
                    "address": address,
                    "script_type": script_type,
                    "spent_by_txid": None,
                    "spent_at_height": None,
                },
            )
            # Same-block spends: later txs in this block resolve these in-memory.
            prevouts[(txid, n)] = (value, address)
            apply_receive(deltas, address=address, value=value, txid=txid)
            block_total_out += value

        in_values: list[Decimal] = []
        if not is_coinbase:
            for vin in vins:
                if _is_mweb(vin):
                    continue
                prev_txid = vin.get("txid")
                prev_n = vin.get("vout")
                if not isinstance(prev_txid, str) or not isinstance(prev_n, int):
                    raise IndexIntegrityError(
                        f"malformed vin in tx {txid}: missing txid/vout",
                    )
                key = (prev_txid, prev_n)
                if key not in prevouts:
                    raise IndexIntegrityError(
                        f"missing prevout {prev_txid}:{prev_n} referenced by tx {txid} "
                        f"at height {height} (index integrity violation)",
                    )
                value, address = prevouts[key]
                in_values.append(value)
                spend_updates.append((prev_txid, prev_n, txid, height))
                apply_spend(deltas, address=address, value=value, txid=txid)

        total_out = sum_values(out_values)
        total_in = sum_values(in_values) if not is_coinbase else ZERO
        fee = compute_fee(total_in=total_in, total_out=total_out, is_coinbase=is_coinbase)
        block_fees += fee

        tx_rows.append(
            {
                "txid": txid,
                "block_height": height,
                "idx": idx,
                "version": tx.get("version"),
                "locktime": tx.get("locktime"),
                "size": tx.get("size"),
                "vsize": tx.get("vsize"),
                "weight": tx.get("weight"),
                "fee": fee,
                "total_in": total_in,
                "total_out": total_out,
                "is_hogex": is_hogex,
            },
        )

    difficulty = block.get("difficulty")
    if difficulty is not None:
        difficulty = _as_decimal(difficulty)

    await conn.execute(
        tables.blocks.insert().values(
            height=height,
            hash=block_hash,
            prev_hash=prev_hash,
            time=int(block["time"]),
            version=block.get("version"),
            bits=str(block["bits"]) if block.get("bits") is not None else None,
            nonce=block.get("nonce"),
            size=block.get("size"),
            weight=block.get("weight"),
            difficulty=difficulty,
            tx_count=len(raw_txs),
            total_out=block_total_out,
            fees=block_fees,
        ),
    )

    if tx_rows:
        await conn.execute(tables.txs.insert(), tx_rows)
    if output_rows:
        await conn.execute(tables.outputs.insert(), output_rows)

    if has_mweb:
        # Narrowed by has_mweb = isinstance(mweb_section, dict).
        mweb_hdr: dict[str, Any] = mweb_section  # type: ignore[assignment]
        aggregated = _aggregate_vkern(raw_txs)
        if aggregated is None:
            pegin, pegout, kernel_fees = _aggregate_mweb_fallback(
                block,
                raw_txs,
                mweb_hdr,
            )
        else:
            pegin, pegout, kernel_fees = aggregated
        await conn.execute(
            tables.mweb_blocks.insert().values(
                height=height,
                hash=_optional_text(mweb_hdr.get("hash")) or block_hash,
                kernel_offset=_optional_text(mweb_hdr.get("kernel_offset")),
                stealth_offset=_optional_text(mweb_hdr.get("stealth_offset")),
                num_kernels=int(mweb_hdr.get("num_kernels") or 0),
                num_txos=int(mweb_hdr.get("num_txos") or 0),
                kernel_root=_optional_text(mweb_hdr.get("kernel_root")),
                output_root=_optional_text(mweb_hdr.get("output_root")),
                leaf_root=_optional_text(mweb_hdr.get("leaf_root")),
                mweb_amount=_mweb_amount_from_block(block, raw_txs),
                pegin=pegin,
                pegout=pegout,
                kernel_fees=kernel_fees,
                hogex_txid=hogex_txid,
            ),
        )

    for prev_txid, prev_n, spent_by, spent_height in spend_updates:
        await conn.execute(
            update(tables.outputs)
            .where(
                tables.outputs.c.txid == prev_txid,
                tables.outputs.c.n == prev_n,
            )
            .values(spent_by_txid=spent_by, spent_at_height=spent_height),
        )

    await _upsert_address_stats(conn, deltas, height=height, reverse=False)
    await _upsert_sync_state(conn, network=network, height=height, tip_hash=block_hash)


async def collect_block_deltas(
    conn: AsyncConnection,
    height: int,
) -> dict[str, AddressDelta]:
    """Rebuild address deltas for a stored block (for rollback)."""
    deltas: dict[str, AddressDelta] = {}

    created = (
        await conn.execute(
            select(
                tables.outputs.c.txid,
                tables.outputs.c.value,
                tables.outputs.c.address,
            ).where(tables.outputs.c.block_height == height),
        )
    ).all()
    for row in created:
        apply_receive(
            deltas,
            address=row.address,
            value=_as_decimal(row.value),
            txid=str(row.txid),
        )

    spent = (
        await conn.execute(
            select(
                tables.outputs.c.value,
                tables.outputs.c.address,
                tables.outputs.c.spent_by_txid,
            ).where(tables.outputs.c.spent_at_height == height),
        )
    ).all()
    for row in spent:
        apply_spend(
            deltas,
            address=row.address,
            value=_as_decimal(row.value),
            txid=str(row.spent_by_txid),
        )

    return deltas


async def rollback_block(
    conn: AsyncConnection,
    height: int,
    *,
    network: str,
) -> None:
    """Reverse one height: address_stats, unspend, delete outputs/block, rewind sync."""
    deltas = await collect_block_deltas(conn, height)
    await _upsert_address_stats(conn, deltas, height=height, reverse=True)

    await conn.execute(
        update(tables.outputs)
        .where(tables.outputs.c.spent_at_height == height)
        .values(spent_by_txid=None, spent_at_height=None),
    )
    await conn.execute(
        tables.outputs.delete().where(tables.outputs.c.block_height == height),
    )
    await conn.execute(
        tables.blocks.delete().where(tables.blocks.c.height == height),
    )

    new_height = height - 1
    if new_height < 0:
        await conn.execute(
            tables.sync_state.delete().where(tables.sync_state.c.network == network),
        )
    else:
        tip_hash = await get_block_hash(conn, new_height)
        if tip_hash is None:
            raise IndexIntegrityError(
                f"missing block at height {new_height} after rollback",
            )
        await _upsert_sync_state(
            conn,
            network=network,
            height=new_height,
            tip_hash=tip_hash,
        )
