"""Unit tests for reorg fork-point detection and rollback last_seen_height."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from explorer.indexer.addresses import AddressDelta
from explorer.indexer.apply import _last_seen_height_before, _upsert_address_stats
from explorer.indexer.reorg import ReorgTooDeepError, find_fork_height


def test_find_fork_at_common_ancestor() -> None:
    # DB and node agree through height 5; diverge at 6+.
    stored = {h: f"hash-{h}" for h in range(8)}
    node = {h: f"hash-{h}" for h in range(6)}
    node[6] = "other-6"
    node[7] = "other-7"
    fork = find_fork_height(
        db_tip_height=7,
        stored_hash_at=stored,
        node_hash_at=node,
        max_reorg_depth=100,
    )
    assert fork == 5


def test_find_fork_full_rewind_within_depth() -> None:
    stored = {0: "old-genesis"}
    node = {0: "new-genesis"}
    fork = find_fork_height(
        db_tip_height=0,
        stored_hash_at=stored,
        node_hash_at=node,
        max_reorg_depth=100,
    )
    assert fork == -1


def test_reorg_too_deep() -> None:
    stored = {h: f"s-{h}" for h in range(10)}
    node = {h: f"n-{h}" for h in range(10)}
    with pytest.raises(ReorgTooDeepError) as exc_info:
        find_fork_height(
            db_tip_height=9,
            stored_hash_at=stored,
            node_hash_at=node,
            max_reorg_depth=3,
        )
    assert exc_info.value.max_depth == 3


@pytest.mark.asyncio
async def test_last_seen_height_before_takes_max_of_create_and_spend() -> None:
    conn = AsyncMock()
    created = MagicMock()
    created.scalar_one.return_value = 4
    spent = MagicMock()
    spent.scalar_one.return_value = 7
    conn.execute = AsyncMock(side_effect=[created, spent])

    height = await _last_seen_height_before(conn, "addr", before_height=10)
    assert height == 7


@pytest.mark.asyncio
async def test_last_seen_height_before_none_when_no_activity() -> None:
    conn = AsyncMock()
    empty = MagicMock()
    empty.scalar_one.return_value = None
    conn.execute = AsyncMock(return_value=empty)

    height = await _last_seen_height_before(conn, "addr", before_height=3)
    assert height is None


def _update_last_seen_is(stmt: object, expected: int) -> bool:
    values = getattr(stmt, "_values", {})
    for key, val in values.items():
        key_name = getattr(key, "name", str(key))
        if key_name == "last_seen_height":
            return int(getattr(val, "value", val)) == expected
    params = stmt.compile().params  # type: ignore[attr-defined]
    return any("last_seen" in pname and int(pval) == expected for pname, pval in params.items())


@pytest.mark.asyncio
async def test_upsert_reverse_sets_last_seen_from_remaining_activity() -> None:
    """Rollback must not blindly set last_seen_height to height-1."""
    existing = SimpleNamespace(
        received=Decimal("10"),
        sent=Decimal("0"),
        balance=Decimal("10"),
        tx_count=2,
        first_seen_height=1,
        last_seen_height=5,
    )
    select_result = MagicMock()
    select_result.one_or_none.return_value = existing

    created_max = MagicMock()
    created_max.scalar_one.return_value = 2
    spent_max = MagicMock()
    spent_max.scalar_one.return_value = None

    update_result = MagicMock()
    conn = AsyncMock()
    conn.execute = AsyncMock(
        side_effect=[select_result, created_max, spent_max, update_result],
    )

    deltas = {
        "addr": AddressDelta(
            received=Decimal("3"),
            sent=Decimal("0"),
            tx_ids={"tx-at-5"},
        ),
    }
    await _upsert_address_stats(conn, deltas, height=5, reverse=True)

    update_call = conn.execute.await_args_list[-1]
    stmt = update_call.args[0]
    # Recomputed from remaining activity (2), not height-1 (4).
    assert _update_last_seen_is(stmt, 2)
