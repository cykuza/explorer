"""Unit tests for fee calculation."""

from __future__ import annotations

from decimal import Decimal

from explorer.indexer.fees import compute_fee, sum_values


def test_coinbase_fee_is_zero() -> None:
    assert compute_fee(
        total_in=Decimal("50"),
        total_out=Decimal("50"),
        is_coinbase=True,
    ) == Decimal("0")


def test_normal_fee() -> None:
    fee = compute_fee(
        total_in=Decimal("1.5"),
        total_out=Decimal("1.499"),
        is_coinbase=False,
    )
    assert fee == Decimal("0.001")
    assert isinstance(fee, Decimal)


def test_sum_values_empty() -> None:
    assert sum_values([]) == Decimal("0")


def test_sum_values_decimals() -> None:
    total = sum_values([Decimal("0.1"), Decimal("0.2"), Decimal("0.3")])
    assert total == Decimal("0.6")
    assert isinstance(total, Decimal)
