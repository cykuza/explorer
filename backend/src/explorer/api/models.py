"""Pydantic response models for API v1 (OpenAPI-complete)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TipResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    height: int
    hash: str
    time: int


class BlockSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    height: int
    hash: str
    time: int
    tx_count: int
    size: int | None
    total_out: str
    fees: str
    has_mweb: bool


class MwebBlockInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    height: int
    hash: str
    kernel_offset: str | None
    stealth_offset: str | None
    num_kernels: int
    num_txos: int
    kernel_root: str | None
    output_root: str | None
    leaf_root: str | None
    mweb_amount: str
    pegin: str
    pegout: str
    kernel_fees: str
    hogex_txid: str | None


class BlockDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    height: int
    hash: str
    prev_hash: str
    next_hash: str | None
    time: int
    version: int | None
    bits: str | None
    nonce: int | None
    size: int | None
    weight: int | None
    difficulty: str | None
    tx_count: int
    total_out: str
    fees: str
    mweb: MwebBlockInfo | None


class TxSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    txid: str
    idx: int
    fee: str
    size: int | None
    total_out: str
    is_hogex: bool
    has_mweb: bool


class LatestTxItem(TxSummary):
    """Confirmed tx in the global recent feed (extends block-scoped TxSummary)."""

    block_height: int
    time: int


class BlockTxPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    page: int
    per_page: int
    txs: list[TxSummary]


class TxVinPrevout(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: str | None
    value: str | None


class TxVin(BaseModel):
    model_config = ConfigDict(extra="allow")

    txid: str | None = None
    vout: int | None = None
    coinbase: str | None = None
    scriptSig: dict[str, Any] | None = None
    sequence: int | None = None
    txinwitness: list[str] | None = None
    ismweb: bool | None = None
    prevout: TxVinPrevout | None = None


class TxVout(BaseModel):
    model_config = ConfigDict(extra="allow")

    n: int
    value: str | None = None
    scriptPubKey: dict[str, Any] | None = None
    ismweb: bool | None = None
    spent_by_txid: str | None = None


class TxDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    txid: str
    hash: str | None = None
    version: int | None = None
    size: int | None = None
    vsize: int | None = None
    weight: int | None = None
    locktime: int | None = None
    vin: list[TxVin]
    vout: list[TxVout]
    hex: str | None = None
    blockhash: str | None = None
    block_height: int | None = None
    idx: int | None = None
    fee: str | None = None
    is_hogex: bool | None = None
    has_mweb: bool
    confirmations: int
    time: int | None = None
    blocktime: int | None = None


class AddressStatsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: str
    balance: str
    received: str
    sent: str
    tx_count: int
    first_seen_height: int
    last_seen_height: int


class AddressTxItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    txid: str
    block_height: int
    time: int
    delta: str
    is_hogex: bool
    has_mweb: bool


class AddressTxPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    page: int
    per_page: int
    txs: list[AddressTxItem]


class MempoolInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int
    vsize: int
    total_fee: str


class MempoolTxItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    txid: str
    has_mweb: bool
    is_hogex: bool = False


class MempoolTxids(BaseModel):
    model_config = ConfigDict(extra="forbid")

    txids: list[str]
    txs: list[MempoolTxItem]


class MwebSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mweb_amount: str
    activation_height: int
    latest: MwebBlockInfo | None
    pegin_24h: str
    pegout_24h: str


class ChartPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    height: int
    time: int
    value: str


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["block", "tx", "address"]
    id: str


class NetworkHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    db_height: int
    node_height: int
    node_headers: int
    ibd: bool
    lag: int


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    networks: dict[str, NetworkHealth]


ChartMetric = Literal["difficulty", "tx_count", "fees", "mweb_amount"]


class PaginationParams(BaseModel):
    """Shared query bounds (documented in OpenAPI via route Query)."""

    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)
