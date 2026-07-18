"""Application settings loaded from EXPLORER_* environment variables."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Network = Literal["mainnet", "testnet", "regtest"]


class Settings(BaseSettings):
    """Runtime configuration. Secrets have no defaults."""

    model_config = SettingsConfigDict(
        env_prefix="EXPLORER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    network: Network
    rpc_url: str
    rpc_user: str
    rpc_password: str
    zmq_rawblock: str
    zmq_hashtx: str
    db_url: str
    db_schema: str | None = Field(default=None)
    sync_poll_interval_sec: int = Field(default=60, ge=1)
    max_reorg_depth: int = Field(default=100, ge=1)

    @model_validator(mode="after")
    def default_schema_to_network(self) -> Self:
        if self.db_schema is None:
            object.__setattr__(self, "db_schema", self.network)
        return self
