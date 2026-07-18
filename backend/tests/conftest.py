"""Integration test fixtures: compose regtest + postgres."""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from sqlalchemy import text

from explorer.config import Settings
from explorer.db import begin, create_engine
from explorer.rpc import RpcClient

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPO_ROOT / "deploy" / "compose.dev.yml"

INTEGRATION_ENV = {
    "EXPLORER_NETWORK": "regtest",
    "EXPLORER_RPC_URL": "http://127.0.0.1:18439",
    "EXPLORER_RPC_USER": "dev",
    "EXPLORER_RPC_PASSWORD": "dev",
    "EXPLORER_ZMQ_RAWBLOCK": "tcp://127.0.0.1:28332",
    "EXPLORER_ZMQ_HASHTX": "tcp://127.0.0.1:28333",
    "EXPLORER_DB_URL": "postgresql+asyncpg://explorer:explorer@127.0.0.1:5432/explorer",
    "EXPLORER_DB_SCHEMA": "regtest",
    "EXPLORER_SYNC_POLL_INTERVAL_SEC": "60",
    "EXPLORER_MAX_REORG_DEPTH": "100",
}


def _compose(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session")
def integration_env() -> Iterator[dict[str, str]]:
    """Ensure EXPLORER_* env is set for Settings / alembic."""
    previous = {key: os.environ.get(key) for key in INTEGRATION_ENV}
    os.environ.update(INTEGRATION_ENV)
    yield dict(INTEGRATION_ENV)
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture(scope="session")
def settings(integration_env: dict[str, str]) -> Settings:
    return Settings()  # type: ignore[call-arg]


async def _wait_rpc(rpc: RpcClient, timeout: float = 120.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            await rpc.call("getblockchaininfo")
            return
        except Exception:
            await asyncio.sleep(1)
    raise RuntimeError("RPC not ready")


async def _wait_db(settings: Settings, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    engine = create_engine(settings)
    try:
        while time.monotonic() < deadline:
            try:
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                return
            except Exception:
                await asyncio.sleep(1)
        raise RuntimeError("Postgres not ready")
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def compose_up(integration_env: dict[str, str], settings: Settings) -> Iterator[None]:
    """Start compose stack (or reuse if already up), migrate, yield."""
    result = _compose("up", "-d", "--wait")
    if result.returncode != 0:
        pytest.fail(
            f"compose up failed:\nstdout={result.stdout}\nstderr={result.stderr}",
        )

    async def _prepare() -> None:
        rpc = RpcClient(
            settings.rpc_url,
            settings.rpc_user,
            settings.rpc_password,
        )
        try:
            await _wait_rpc(rpc)
            await _wait_db(settings)
        finally:
            await rpc.aclose()

        mig = subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            cwd=REPO_ROOT / "backend",
            env={**os.environ, **integration_env},
            check=False,
            capture_output=True,
            text=True,
        )
        if mig.returncode != 0:
            raise RuntimeError(f"alembic failed:\n{mig.stdout}\n{mig.stderr}")

    asyncio.run(_prepare())
    yield


@pytest.fixture
async def rpc(settings: Settings, compose_up: None) -> AsyncIterator[RpcClient]:
    """Wallet-scoped RPC client (``/wallet/testwallet``) for reliable wallet calls."""
    from tests.helpers import ensure_wallet, wallet_rpc_url

    bootstrap = RpcClient(settings.rpc_url, settings.rpc_user, settings.rpc_password)
    try:
        await ensure_wallet(bootstrap, "testwallet")
    finally:
        await bootstrap.aclose()

    client = RpcClient(
        wallet_rpc_url(settings.rpc_url, "testwallet"),
        settings.rpc_user,
        settings.rpc_password,
    )
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture(autouse=True)
async def require_empty_mempool(request: pytest.FixtureRequest) -> AsyncIterator[None]:
    """Integration invariant: shared regtest mempool must be empty around each test.

    A leftover tx (or a tip stuck needing a peg-in after a bad activation) poisons
    every later ``generatetoaddress``. Fail with the offending txids named.
    """
    if request.node.get_closest_marker("integration") is None:
        yield
        return

    settings: Settings = request.getfixturevalue("settings")
    request.getfixturevalue("compose_up")
    rpc = RpcClient(settings.rpc_url, settings.rpc_user, settings.rpc_password)
    try:
        before = await rpc.call("getrawmempool")
        if not isinstance(before, list):
            pytest.fail(f"getrawmempool returned non-list at test start: {before!r}")
        if before:
            pytest.fail(f"mempool not empty at test start: {before}")
        yield
        after = await rpc.call("getrawmempool")
        if not isinstance(after, list):
            pytest.fail(f"getrawmempool returned non-list at test end: {after!r}")
        if after:
            pytest.fail(f"mempool not empty at test end: {after}")
    finally:
        await rpc.aclose()


@pytest.fixture
async def clean_index(settings: Settings, compose_up: None) -> AsyncIterator[None]:
    """Truncate indexer tables between tests."""
    schema = settings.db_schema
    assert schema is not None
    engine = create_engine(settings)
    async with begin(engine, schema) as conn:
        await conn.execute(
            text(
                "TRUNCATE address_stats, outputs, txs, mweb_blocks, blocks, sync_state "
                "RESTART IDENTITY CASCADE",
            ),
        )
    await engine.dispose()
    yield
