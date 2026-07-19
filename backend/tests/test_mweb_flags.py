"""Unit tests for MWEB flag detection helpers."""

from __future__ import annotations

from explorer.api.mweb_flags import has_mweb_flag, has_mweb_from_raw


def test_has_mweb_flag() -> None:
    assert has_mweb_flag(is_hogex=True, has_pegin=False) is True
    assert has_mweb_flag(is_hogex=False, has_pegin=True) is True
    assert has_mweb_flag(is_hogex=False, has_pegin=False) is False


def test_has_mweb_from_raw_pegin() -> None:
    raw = {
        "vin": [],
        "vout": [
            {"n": 0, "scriptPubKey": {"type": "witness_mweb_pegin"}},
        ],
    }
    assert has_mweb_from_raw(raw) is True


def test_has_mweb_from_raw_ismweb() -> None:
    assert has_mweb_from_raw({"vin": [{"ismweb": True}], "vout": []}) is True
    assert has_mweb_from_raw({"vin": [], "vout": [{"ismweb": True}]}) is True


def test_has_mweb_from_raw_plain() -> None:
    raw = {
        "vin": [{"txid": "ab", "vout": 0}],
        "vout": [{"n": 0, "scriptPubKey": {"type": "pubkeyhash"}}],
    }
    assert has_mweb_from_raw(raw) is False
    assert has_mweb_from_raw(raw, is_hogex=True) is True
