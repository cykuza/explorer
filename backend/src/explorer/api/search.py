"""Search query classification (pure; DB/RPC lookups happen in the route)."""

from __future__ import annotations

import re
from typing import Literal

SearchKind = Literal["block_height", "hex64", "address"]

_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_DIGITS = re.compile(r"^[0-9]+$")


def classify_query(q: str, tip_height: int) -> SearchKind | None:
    """Classify a search string before resolving against the index/node.

    - All digits and ``int(q) <= tip_height`` → block height candidate.
    - Exactly 64 hex chars → block hash or txid candidate (also covers
      digit-only hashes that exceeded tip).
    - Otherwise → address candidate (caller checks ``address_stats``).
    """
    if _DIGITS.fullmatch(q):
        height = int(q)
        if height <= tip_height:
            return "block_height"
    if _HEX64.fullmatch(q):
        return "hex64"
    if q:
        return "address"
    return None
