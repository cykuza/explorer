"""Tests for ApiSettings parsing and API engine connect options."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from explorer.api.app import api_engine_kwargs
from explorer.api.settings import ApiSettings

REQUIRED_ENV = {
    "EXPLORER_API_NETWORKS": "regtest",
    "EXPLORER_DB_URL": "postgresql+asyncpg://dev:dev@127.0.0.1:5432/explorer",
    "EXPLORER_REGTEST_RPC_URL": "http://127.0.0.1:18439",
    "EXPLORER_REGTEST_RPC_USER": "dev",
    "EXPLORER_REGTEST_RPC_PASSWORD": "dev",
}


def _set_required(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)


def test_api_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required(monkeypatch)
    monkeypatch.delenv("EXPLORER_DB_STATEMENT_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("EXPLORER_API_LIMIT_CONCURRENCY", raising=False)

    settings = ApiSettings()  # type: ignore[call-arg]

    assert settings.db_statement_timeout_ms == 5000
    assert settings.api_limit_concurrency == 100


def test_api_settings_timeout_and_concurrency_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required(monkeypatch)
    monkeypatch.setenv("EXPLORER_DB_STATEMENT_TIMEOUT_MS", "2500")
    monkeypatch.setenv("EXPLORER_API_LIMIT_CONCURRENCY", "50")

    settings = ApiSettings()  # type: ignore[call-arg]

    assert settings.db_statement_timeout_ms == 2500
    assert settings.api_limit_concurrency == 50


def test_api_engine_kwargs_sets_statement_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required(monkeypatch)
    monkeypatch.setenv("EXPLORER_DB_STATEMENT_TIMEOUT_MS", "7500")

    settings = ApiSettings()  # type: ignore[call-arg]
    kwargs = api_engine_kwargs(settings)

    assert kwargs["pool_pre_ping"] is True
    assert kwargs["connect_args"]["server_settings"]["statement_timeout"] == "7500"


@pytest.mark.parametrize("bad", ["0", "-1"])
def test_api_limit_concurrency_rejects_non_positive(
    monkeypatch: pytest.MonkeyPatch,
    bad: str,
) -> None:
    _set_required(monkeypatch)
    monkeypatch.setenv("EXPLORER_API_LIMIT_CONCURRENCY", bad)

    with pytest.raises(ValidationError):
        ApiSettings()  # type: ignore[call-arg]
