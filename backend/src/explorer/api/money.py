"""Monetary amount serialization (always 8 decimal places, never float)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

EIGHT_DP = Decimal("0.00000001")


def decimal_str(value: Decimal | int | str) -> str:
    """Format an amount as a fixed 8-decimal-place string."""
    amount = value if isinstance(value, Decimal) else Decimal(value)
    quantized = amount.quantize(EIGHT_DP, rounding=ROUND_HALF_UP)
    return format(quantized, "f")
