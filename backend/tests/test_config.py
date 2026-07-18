"""Tests for Settings parsing from environment."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from explorer.config import Settings

REQUIRED_ENV = {
    "EXPLORER_NETWORK": "regtest",
    "EXPLORER_RPC_URL": "http://127.0.0.1:18443",
    "EXPLORER_RPC_USER": "dev",
    "EXPLORER_RPC_PASSWORD": "dev",
    "EXPLORER_ZMQ_RAWBLOCK": "tcp://127.0.0.1:28332",
    "EXPLORER_ZMQ_HASHTX": "tcp://127.0.0.1:28333",
    "EXPLORER_DB_URL": "postgresql+asyncpg://dev:dev@127.0.0.1:5432/explorer",
}


def test_settings_parses_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("EXPLORER_DB_SCHEMA", raising=False)

    settings = Settings()  # type: ignore[call-arg]  # fields from env

    assert settings.network == "regtest"
    assert settings.rpc_url == "http://127.0.0.1:18443"
    assert settings.rpc_user == "dev"
    assert settings.rpc_password == "dev"
    assert settings.zmq_rawblock == "tcp://127.0.0.1:28332"
    assert settings.zmq_hashtx == "tcp://127.0.0.1:28333"
    assert settings.db_url == "postgresql+asyncpg://dev:dev@127.0.0.1:5432/explorer"
    assert settings.db_schema == "regtest"


def test_settings_explicit_db_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("EXPLORER_DB_SCHEMA", "custom")

    settings = Settings()  # type: ignore[call-arg]  # fields from env

    assert settings.db_schema == "custom"


@pytest.mark.parametrize(
    "missing",
    [
        "EXPLORER_NETWORK",
        "EXPLORER_RPC_URL",
        "EXPLORER_RPC_USER",
        "EXPLORER_RPC_PASSWORD",
        "EXPLORER_ZMQ_RAWBLOCK",
        "EXPLORER_ZMQ_HASHTX",
        "EXPLORER_DB_URL",
    ],
)
def test_settings_missing_required_raises(
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv(missing, raising=False)

    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]  # intentional missing env
