"""Async SQLAlchemy engine helpers with schema search_path."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from explorer.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Create an async engine for the configured database URL."""
    return create_async_engine(settings.db_url, pool_pre_ping=True)


@asynccontextmanager
async def connect(engine: AsyncEngine, schema: str) -> AsyncIterator[AsyncConnection]:
    """Yield a connection with ``search_path`` set to the explorer schema."""
    async with engine.connect() as conn:
        await conn.execute(text(f'SET search_path TO "{schema}"'))
        yield conn


@asynccontextmanager
async def begin(engine: AsyncEngine, schema: str) -> AsyncIterator[AsyncConnection]:
    """Yield a transactional connection with ``search_path`` set."""
    async with engine.begin() as conn:
        await conn.execute(text(f'SET search_path TO "{schema}"'))
        yield conn
