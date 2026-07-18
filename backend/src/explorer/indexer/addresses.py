"""Address extraction and address_stats delta aggregation."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

ZERO = Decimal("0")


def extract_address(script_pub_key: dict[str, Any]) -> str | None:
    """Return the first address from a scriptPubKey, or None."""
    addresses = script_pub_key.get("addresses")
    if isinstance(addresses, list) and addresses:
        first = addresses[0]
        if isinstance(first, str) and first:
            return first
    address = script_pub_key.get("address")
    if isinstance(address, str) and address:
        return address
    return None


def extract_script_type(script_pub_key: dict[str, Any]) -> str:
    """Return script type string, defaulting to ``unknown``."""
    script_type = script_pub_key.get("type")
    if isinstance(script_type, str) and script_type:
        return script_type
    return "unknown"


@dataclass
class AddressDelta:
    """Accumulated address_stats change for one address within a block apply/rollback."""

    received: Decimal = ZERO
    sent: Decimal = ZERO
    tx_ids: set[str] = field(default_factory=set)

    @property
    def balance(self) -> Decimal:
        return self.received - self.sent

    @property
    def tx_count(self) -> int:
        return len(self.tx_ids)


def apply_receive(
    deltas: dict[str, AddressDelta],
    *,
    address: str | None,
    value: Decimal,
    txid: str,
) -> None:
    """Record a received output toward address stats (no-op if address is None)."""
    if address is None:
        return
    delta = deltas.setdefault(address, AddressDelta())
    delta.received += value
    delta.tx_ids.add(txid)


def apply_spend(
    deltas: dict[str, AddressDelta],
    *,
    address: str | None,
    value: Decimal,
    txid: str,
) -> None:
    """Record a spent prevout toward address stats (no-op if address is None)."""
    if address is None:
        return
    delta = deltas.setdefault(address, AddressDelta())
    delta.sent += value
    delta.tx_ids.add(txid)


def negate_deltas(deltas: dict[str, AddressDelta]) -> dict[str, AddressDelta]:
    """Return deltas with received/sent signs flipped (for reorg rollback)."""
    result: dict[str, AddressDelta] = {}
    for address, delta in deltas.items():
        result[address] = AddressDelta(
            received=-delta.received,
            sent=-delta.sent,
            tx_ids=set(delta.tx_ids),
        )
    return result
