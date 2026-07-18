"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from explorer.api.context import NetworkContext
from explorer.api.problems import register_exception_handlers
from explorer.api.routes import health_router, router
from explorer.api.settings import ApiSettings
from explorer.config import Network
from explorer.rpc import RpcClient


def _build_contexts(
    settings: ApiSettings,
    engine: AsyncEngine,
    *,
    rpc_overrides: dict[Network, RpcClient] | None = None,
) -> dict[Network, NetworkContext]:
    contexts: dict[Network, NetworkContext] = {}
    for network in settings.api_networks:
        if rpc_overrides is not None and network in rpc_overrides:
            rpc = rpc_overrides[network]
        else:
            cfg = settings.network_rpc[network]
            rpc = RpcClient(cfg.url, cfg.user, cfg.password)
        contexts[network] = NetworkContext(
            network=network,
            schema=settings.schema_for(network),
            engine=engine,
            rpc=rpc,
        )
    return contexts


def create_app(
    settings: ApiSettings | None = None,
    *,
    contexts: dict[Network, NetworkContext] | None = None,
    engine: AsyncEngine | None = None,
) -> FastAPI:
    """Build the API app.

    For tests, pass pre-built ``contexts`` (and optionally ``engine``) to skip
    env-based lifespan setup.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        own_engine = False
        own_rpcs = False
        if getattr(app.state, "contexts", None) is None:
            cfg: ApiSettings = app.state.settings
            eng = create_async_engine(cfg.db_url, pool_pre_ping=True)
            app.state.engine = eng
            app.state.contexts = _build_contexts(cfg, eng)
            own_engine = True
            own_rpcs = True
        try:
            yield
        finally:
            if own_rpcs:
                for ctx in app.state.contexts.values():
                    await ctx.rpc.aclose()
            if own_engine and getattr(app.state, "engine", None) is not None:
                await app.state.engine.dispose()

    app = FastAPI(
        title="Cyberyen Explorer API",
        version="1.0.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.include_router(health_router)

    if settings is not None:
        app.state.settings = settings
    if contexts is not None:
        app.state.contexts = contexts
    if engine is not None:
        app.state.engine = engine

    return app


def app_factory() -> FastAPI:
    """Uvicorn factory: ``uvicorn explorer.api.app:app_factory --factory``."""
    settings = ApiSettings()  # type: ignore[call-arg]
    return create_app(settings)


# Module-level app for ``uvicorn explorer.api.app:app`` when env is set at import.
app: Any = None
