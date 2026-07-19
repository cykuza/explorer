"""Unit tests for migrate-on-sync ownership."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from explorer.migrate import _find_alembic_ini, upgrade_head

REQUIRED_ENV = {
    "EXPLORER_NETWORK": "regtest",
    "EXPLORER_RPC_URL": "http://127.0.0.1:18443",
    "EXPLORER_RPC_USER": "dev",
    "EXPLORER_RPC_PASSWORD": "dev",
    "EXPLORER_ZMQ_RAWBLOCK": "tcp://127.0.0.1:28332",
    "EXPLORER_ZMQ_HASHTX": "tcp://127.0.0.1:28333",
    "EXPLORER_DB_URL": "postgresql+asyncpg://dev:dev@127.0.0.1:5432/explorer",
}


def test_find_alembic_ini_from_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ini = tmp_path / "alembic.ini"
    ini.write_text("[alembic]\nscript_location = migrations\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert _find_alembic_ini() == ini.resolve()


def test_find_alembic_ini_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError, match="alembic.ini"):
        _find_alembic_ini()


def test_upgrade_head_calls_alembic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ini = tmp_path / "alembic.ini"
    ini.write_text("[alembic]\nscript_location = migrations\n", encoding="utf-8")
    upgrade = MagicMock()
    monkeypatch.setattr("explorer.migrate.command.upgrade", upgrade)

    upgrade_head(ini_path=ini)

    upgrade.assert_called_once()
    cfg, revision = upgrade.call_args.args
    assert revision == "head"
    assert cfg.config_file_name == str(ini)


def test_sync_runs_upgrade_before_run_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)

    calls: list[str] = []

    def fake_upgrade() -> None:
        calls.append("upgrade")

    async def fake_run_sync(*_args: Any, **_kwargs: Any) -> None:
        calls.append("sync")

    monkeypatch.setattr("explorer.migrate.upgrade_head", fake_upgrade)
    monkeypatch.setattr("explorer.indexer.sync.run_sync", fake_run_sync)

    from explorer.__main__ import main

    assert main(["sync", "--once"]) == 0
    assert calls == ["upgrade", "sync"]


def test_api_does_not_migrate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPLORER_API_NETWORKS", "regtest")
    monkeypatch.setenv("EXPLORER_DB_URL", REQUIRED_ENV["EXPLORER_DB_URL"])
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_URL", "http://127.0.0.1:18443")
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_USER", "dev")
    monkeypatch.setenv("EXPLORER_REGTEST_RPC_PASSWORD", "dev")

    upgrade = MagicMock()
    monkeypatch.setattr("explorer.migrate.upgrade_head", upgrade)

    def fake_uvicorn_run(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr("uvicorn.run", fake_uvicorn_run)

    from explorer.__main__ import main

    assert main(["api", "--host", "127.0.0.1", "--port", "9"]) == 0
    upgrade.assert_not_called()
