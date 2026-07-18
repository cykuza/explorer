"""Unit tests for address extraction and delta aggregation."""

from __future__ import annotations

from decimal import Decimal

from explorer.indexer.addresses import (
    AddressDelta,
    apply_receive,
    apply_spend,
    extract_address,
    extract_script_type,
    negate_deltas,
)


def test_extract_address_from_addresses_list() -> None:
    spk = {"addresses": ["rcy1qabc"], "type": "witness_v0_keyhash"}
    assert extract_address(spk) == "rcy1qabc"


def test_extract_address_from_address_field() -> None:
    spk = {"address": "rcy1qxyz", "type": "witness_v0_keyhash"}
    assert extract_address(spk) == "rcy1qxyz"


def test_extract_address_none_for_nulldata() -> None:
    assert extract_address({"type": "nulldata"}) is None


def test_extract_script_type_default() -> None:
    assert extract_script_type({}) == "unknown"
    assert extract_script_type({"type": "pubkeyhash"}) == "pubkeyhash"


def test_null_address_excluded_from_deltas() -> None:
    deltas: dict[str, AddressDelta] = {}
    apply_receive(deltas, address=None, value=Decimal("1"), txid="aa")
    apply_spend(deltas, address=None, value=Decimal("1"), txid="bb")
    assert deltas == {}


def test_delta_aggregation_and_tx_count() -> None:
    deltas: dict[str, AddressDelta] = {}
    apply_receive(deltas, address="A", value=Decimal("10"), txid="tx1")
    apply_receive(deltas, address="A", value=Decimal("5"), txid="tx1")
    apply_spend(deltas, address="A", value=Decimal("3"), txid="tx2")
    delta = deltas["A"]
    assert delta.received == Decimal("15")
    assert delta.sent == Decimal("3")
    assert delta.balance == Decimal("12")
    assert delta.tx_count == 2  # tx1 and tx2 once each


def test_negate_deltas() -> None:
    deltas = {
        "A": AddressDelta(
            received=Decimal("10"),
            sent=Decimal("2"),
            tx_ids={"t1"},
        ),
    }
    negated = negate_deltas(deltas)
    assert negated["A"].received == Decimal("-10")
    assert negated["A"].sent == Decimal("-2")
    assert negated["A"].balance == Decimal("-8")
