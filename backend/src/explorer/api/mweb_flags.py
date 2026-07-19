"""Detect MWEB involvement on L1 transactions (for list/detail badges)."""

from __future__ import annotations

from typing import Any

PEGIN_SCRIPT_TYPE = "witness_mweb_pegin"


def has_mweb_from_raw(raw: dict[str, Any], *, is_hogex: bool = False) -> bool:
    """True if HogEx, peg-in output, or any ``ismweb`` vin/vout."""
    if is_hogex:
        return True
    for vin in raw.get("vin") or []:
        if isinstance(vin, dict) and vin.get("ismweb"):
            return True
    for vout in raw.get("vout") or []:
        if not isinstance(vout, dict):
            continue
        if vout.get("ismweb"):
            return True
        spk = vout.get("scriptPubKey") or {}
        if isinstance(spk, dict) and spk.get("type") == PEGIN_SCRIPT_TYPE:
            return True
    return False


def has_mweb_flag(*, is_hogex: bool, has_pegin: bool) -> bool:
    """DB-oriented detection when only ``is_hogex`` and peg-in outputs are known."""
    return bool(is_hogex or has_pegin)
