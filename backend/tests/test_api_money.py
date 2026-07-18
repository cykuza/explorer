"""Unit tests for monetary string serialization."""

from __future__ import annotations

from decimal import Decimal

from explorer.api.money import decimal_str


def test_eight_decimal_places() -> None:
    assert decimal_str(Decimal("1")) == "1.00000000"
    assert decimal_str(Decimal("0.1")) == "0.10000000"
    assert decimal_str("50.5") == "50.50000000"
    assert decimal_str(0) == "0.00000000"


def test_rounding_half_up() -> None:
    assert decimal_str(Decimal("1.000000005")) == "1.00000001"
    assert decimal_str(Decimal("1.000000004")) == "1.00000000"
