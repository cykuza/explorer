"""Unit tests for MWEB activation height derivation."""

from __future__ import annotations

from typing import Any

import pytest

from tests.helpers import predict_mweb_activation_height


def _info(mweb: dict[str, Any], *, period: int = 144) -> dict[str, Any]:
    return {
        "blocks": 0,
        "softforks": {
            "testdummy": {
                "type": "bip9",
                "bip9": {
                    "status": "started",
                    "since": period,
                    "statistics": {"period": period, "threshold": 108},
                },
            },
            "mweb": mweb,
        },
    }


def test_predict_active_uses_height() -> None:
    info = _info(
        {
            "type": "bip8",
            "active": True,
            "height": 432,
            "bip8": {"status": "active", "since": 432, "start_height": 0, "timeout_height": 0},
        },
    )
    assert predict_mweb_activation_height(info) == 432


def test_predict_locked_in_is_since_plus_period() -> None:
    info = _info(
        {
            "type": "bip8",
            "active": False,
            "bip8": {
                "status": "locked_in",
                "since": 288,
                "start_height": 0,
                "timeout_height": 0,
            },
        },
    )
    assert predict_mweb_activation_height(info) == 288 + 144


def test_predict_started_is_since_plus_two_periods() -> None:
    info = _info(
        {
            "type": "bip8",
            "active": False,
            "bip8": {
                "status": "started",
                "since": 144,
                "start_height": 0,
                "timeout_height": 0,
                "statistics": {"period": 144, "threshold": 108},
            },
        },
    )
    assert predict_mweb_activation_height(info) == 144 + 2 * 144


def test_predict_defined_returns_none() -> None:
    info = _info(
        {
            "type": "bip8",
            "active": False,
            "bip8": {
                "status": "defined",
                "since": 0,
                "start_height": 0,
                "timeout_height": 0,
            },
        },
    )
    assert predict_mweb_activation_height(info) is None


def test_predict_missing_period_raises() -> None:
    info = {
        "softforks": {
            "mweb": {
                "active": False,
                "bip8": {"status": "locked_in", "since": 288},
            },
        },
    }
    with pytest.raises(RuntimeError, match="confirmation window"):
        predict_mweb_activation_height(info)
