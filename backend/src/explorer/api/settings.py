"""API process settings: multi-network RPC + shared DB."""

from __future__ import annotations

import os
from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from explorer.config import Network

MWEB_ACTIVATION_HEIGHT: dict[Network, int] = {
    "mainnet": 2880,
    "testnet": 2880,
    "regtest": 432,
}


class NetworkRpcConfig:
    """RPC credentials for one network."""

    __slots__ = ("url", "user", "password")

    def __init__(self, url: str, user: str, password: str) -> None:
        self.url = url
        self.user = user
        self.password = password


class ApiSettings(BaseSettings):
    """Runtime configuration for the read-only API process."""

    model_config = SettingsConfigDict(
        env_prefix="EXPLORER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_networks: Annotated[list[Network], NoDecode]
    db_url: str
    api_max_lag: int = Field(default=10, ge=0)
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8080, ge=1, le=65535)
    api_sse_poll_sec: float = Field(default=2, gt=0)
    db_statement_timeout_ms: int = Field(default=5000, ge=0)
    api_limit_concurrency: int = Field(default=100, ge=1)

    # Populated by model_validator from EXPLORER_<NETWORK>_RPC_* env vars.
    network_rpc: dict[Network, NetworkRpcConfig] = Field(
        default_factory=dict,
        exclude=True,
    )

    @field_validator("api_networks", mode="before")
    @classmethod
    def split_networks(cls, value: object) -> object:
        if isinstance(value, str):
            parts = [p.strip() for p in value.split(",") if p.strip()]
            return parts
        return value

    @model_validator(mode="after")
    def load_per_network_rpc(self) -> Self:
        rpc: dict[Network, NetworkRpcConfig] = {}
        for network in self.api_networks:
            prefix = f"EXPLORER_{network.upper()}_RPC_"
            url = os.environ.get(f"{prefix}URL")
            user = os.environ.get(f"{prefix}USER")
            password = os.environ.get(f"{prefix}PASSWORD")
            missing = [
                name
                for name, val in (
                    (f"{prefix}URL", url),
                    (f"{prefix}USER", user),
                    (f"{prefix}PASSWORD", password),
                )
                if not val
            ]
            if missing:
                raise ValueError(
                    f"missing RPC env for network {network!r}: {', '.join(missing)}",
                )
            assert url is not None and user is not None and password is not None
            rpc[network] = NetworkRpcConfig(url, user, password)
        object.__setattr__(self, "network_rpc", rpc)
        return self

    def schema_for(self, network: Network) -> str:
        """DB schema name equals the network name."""
        return network
