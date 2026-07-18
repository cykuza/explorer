"""Pure fee / total calculation helpers (Decimal only)."""

from __future__ import annotations

from decimal import Decimal

ZERO = Decimal("0")


def compute_fee(*, total_in: Decimal, total_out: Decimal, is_coinbase: bool) -> Decimal:
    """Return fee as ``total_in - total_out``, or 0 for coinbase."""
    if is_coinbase:
        return ZERO
    return total_in - total_out


def sum_values(values: list[Decimal]) -> Decimal:
    """Sum Decimal amounts (empty → 0)."""
    total = ZERO
    for value in values:
        total += value
    return total
