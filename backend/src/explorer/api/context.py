"""Per-network runtime context (engine schema + RPC)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from explorer.config import Network
from explorer.rpc import RpcClient


@dataclass
class NetworkContext:
    """Read-only resources for one configured network."""

    network: Network
    schema: str
    engine: AsyncEngine
    rpc: RpcClient
