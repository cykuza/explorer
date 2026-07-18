"""FastAPI dependencies for network path resolution."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request

from explorer.api.context import NetworkContext
from explorer.api.problems import raise_problem
from explorer.api.settings import ApiSettings
from explorer.config import Network

VALID_NETWORKS: frozenset[str] = frozenset({"mainnet", "testnet", "regtest"})


def get_api_settings(request: Request) -> ApiSettings:
    return cast(ApiSettings, request.app.state.settings)


def get_contexts(request: Request) -> dict[Network, NetworkContext]:
    return cast(dict[Network, NetworkContext], request.app.state.contexts)


def get_network_context(request: Request, network: str) -> NetworkContext:
    if network not in VALID_NETWORKS:
        raise_problem(404, "Not Found", f"Unknown network: {network}")
    contexts = get_contexts(request)
    ctx = contexts.get(cast(Network, network))
    if ctx is None:
        raise_problem(404, "Not Found", f"Unknown network: {network}")
    return ctx


NetworkCtx = Annotated[NetworkContext, Depends(get_network_context)]
