"""Unit tests for search query classification."""

from __future__ import annotations

from explorer.api.search import classify_query


def test_classify_block_height() -> None:
    assert classify_query("0", tip_height=100) == "block_height"
    assert classify_query("100", tip_height=100) == "block_height"


def test_classify_digits_above_tip_as_address() -> None:
    assert classify_query("101", tip_height=100) == "address"


def test_classify_digit_only_hex64() -> None:
    """64 digit chars are a hash/txid, not an address, even when > tip."""
    assert classify_query("4" * 64, tip_height=10) == "hex64"


def test_classify_hex64() -> None:
    q = "a" * 64
    assert classify_query(q, tip_height=10) == "hex64"
    assert classify_query("A" * 64, tip_height=10) == "hex64"


def test_classify_address() -> None:
    assert classify_query("rcy1qexample", tip_height=10) == "address"


def test_classify_empty() -> None:
    assert classify_query("", tip_height=10) is None
