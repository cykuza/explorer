"""Chain / softfork helpers derived from ``getblockchaininfo``."""

from __future__ import annotations

from typing import Any


def softfork_entry(info: dict[str, Any], name: str) -> dict[str, Any] | None:
    softforks = info.get("softforks") or info.get("bip9_softforks") or {}
    if not isinstance(softforks, dict):
        return None
    entry = softforks.get(name)
    return entry if isinstance(entry, dict) else None


def softfork_bip(entry: dict[str, Any]) -> dict[str, Any]:
    bip = entry.get("bip8") or entry.get("bip9") or {}
    return bip if isinstance(bip, dict) else {}


def softfork_active(info: dict[str, Any], name: str) -> bool:
    entry = softfork_entry(info, name)
    if entry is None:
        return False
    if entry.get("active") is True:
        return True
    status = entry.get("status")
    if isinstance(status, str) and status.lower() == "active":
        return True
    bip = softfork_bip(entry)
    bip_status = bip.get("status")
    return isinstance(bip_status, str) and bip_status.lower() == "active"


def miner_confirmation_window(info: dict[str, Any]) -> int:
    """BIP period from any softfork ``statistics.period`` (same nMinerConfirmationWindow)."""
    softforks = info.get("softforks") or {}
    if not isinstance(softforks, dict):
        raise RuntimeError("getblockchaininfo.softforks missing")
    for entry in softforks.values():
        if not isinstance(entry, dict):
            continue
        bip = softfork_bip(entry)
        stats = bip.get("statistics") or {}
        if isinstance(stats, dict) and stats.get("period") is not None:
            return int(stats["period"])
    raise RuntimeError(
        "cannot derive miner confirmation window: no softfork statistics.period",
    )


def predict_mweb_activation_height(info: dict[str, Any]) -> int | None:
    """Return MWEB activation height from ``getblockchaininfo``, or None if still defined.

    Uses ``softforks.mweb`` status/since/height plus ``statistics.period`` from any
    deployment (testdummy while mweb has no stats). Does not hardcode 430/431/432.
    """
    mweb = softfork_entry(info, "mweb") or softfork_entry(info, "MWEB")
    if mweb is None:
        raise RuntimeError("mweb softfork missing from getblockchaininfo")
    bip = softfork_bip(mweb)
    status = str(bip.get("status") or mweb.get("status") or "").lower()

    if mweb.get("active") is True or status == "active":
        if mweb.get("height") is not None:
            return int(mweb["height"])
        if bip.get("since") is not None:
            return int(bip["since"])
        raise RuntimeError(f"mweb active but no height/since: {mweb}")

    if status == "defined":
        return None

    period = miner_confirmation_window(info)
    if status == "locked_in":
        # ACTIVE begins at the next period boundary after locked_in.since.
        return int(bip["since"]) + period
    if status == "started":
        # Height-based timeout_height==start_height forces LOCKED_IN at the end of
        # this period, then ACTIVE after one more period.
        return int(bip["since"]) + 2 * period
    raise RuntimeError(f"unhandled mweb softfork status {status!r}: {mweb}")
