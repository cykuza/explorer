"""Shared helpers for tests (unit + integration)."""

from __future__ import annotations

from decimal import Decimal

from explorer.chain import (
    predict_mweb_activation_height,
    softfork_active,
    softfork_bip,
    softfork_entry,
)
from explorer.rpc import RpcClient
from explorer.wallet import (
    ensure_wallet,
    mine_to,
    mweb_address,
    rpc_root_url,
    wallet_rpc_url,
)

# Re-export for existing test imports.
__all__ = [
    "address_unspent_balance",
    "activate_mweb",
    "as_decimal",
    "ensure_wallet",
    "mine_to",
    "mweb_address",
    "predict_mweb_activation_height",
    "rpc_root_url",
    "wallet_rpc_url",
]


async def address_unspent_balance(rpc: RpcClient, address: str) -> Decimal:
    unspent = await rpc.call("listunspent", 0, 9999999, [address])
    assert isinstance(unspent, list)
    total = Decimal("0")
    for entry in unspent:
        total += as_decimal(entry["amount"])
    return total


def as_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


# Backward-compatible private aliases used by older test code paths.
_softfork_entry = softfork_entry
_softfork_bip = softfork_bip
_softfork_active = softfork_active


async def activate_mweb(rpc: RpcClient, mine_address: str) -> int:
    """Deterministically activate MWEB: mine to activation−1, peg-in, mine activation.

    Refuses to ``sendtoaddress`` an MWEB destination at any other tip. The first
    post-activation block must include ≥1 peg-in or CreateNewBlock fails with
    ``bad-txns-vin-empty`` (empty HogEx vin).

    Note: ``getblockchaininfo`` may report mweb ``active`` with ``height``/
    ``since`` equal to the upcoming activation block while tip is still
    ``activation - 1`` (LOCKED_IN tip, next block is ACTIVE).
    """
    while True:
        info = await rpc.call("getblockchaininfo")
        assert isinstance(info, dict)
        tip = int(info.get("blocks") or await rpc.call("getblockcount"))
        mweb = softfork_entry(info, "mweb") or softfork_entry(info, "MWEB")
        assert mweb is not None
        bip = softfork_bip(mweb)

        activation = predict_mweb_activation_height(info)
        if activation is None:
            await mine_to(rpc, mine_address, 25)
            continue

        # Activation block already on chain.
        if tip >= activation and (softfork_active(info, "mweb") or softfork_active(info, "MWEB")):
            block = await rpc.call("getblock", await rpc.call("getblockhash", activation), 2)
            assert isinstance(block, dict)
            if "mweb" not in block:
                raise RuntimeError(
                    f"activation height {activation} mined but block lacks mweb section",
                )
            print(f"MWEB_ACTIVATION_HEIGHT={activation} tip={tip} fields={bip}")
            return activation

        if tip < activation - 1:
            n = min(25, (activation - 1) - tip)
            await mine_to(rpc, mine_address, n)
            continue

        if tip > activation - 1:
            raise RuntimeError(
                f"tip {tip} is past activation-1={activation - 1} but activation "
                f"block {activation} is not present; chain needs a peg-in before "
                f"mining block {activation}.",
            )

        # tip == activation - 1: only legal height for the mandatory activation peg-in.
        mempool = await rpc.call("getrawmempool")
        if isinstance(mempool, list) and mempool:
            raise RuntimeError(
                f"mempool not empty before activation peg-in at tip {tip}: {mempool}",
            )
        mweb_addr = await mweb_address(rpc)
        pegin_txid = str(await rpc.call("sendtoaddress", mweb_addr, "1"))
        print(
            f"MWEB_ACTIVATION_PEGIN tip={tip} activation={activation} "
            f"txid={pegin_txid} addr={mweb_addr}",
        )
        await mine_to(rpc, mine_address, 1)

        info2 = await rpc.call("getblockchaininfo")
        assert isinstance(info2, dict)
        tip2 = int(info2.get("blocks") or 0)
        if tip2 != activation:
            raise RuntimeError(
                f"expected tip==activation {activation} after peg-in mine, got {tip2}",
            )
        if not (softfork_active(info2, "mweb") or softfork_active(info2, "MWEB")):
            raise RuntimeError(f"mweb not active after activation block at tip {tip2}")
        block_hash = str(await rpc.call("getblockhash", tip2))
        block = await rpc.call("getblock", block_hash, 2)
        assert isinstance(block, dict)
        if "mweb" not in block:
            raise RuntimeError(f"activation block {tip2} missing mweb section")
        txs = block.get("tx") or []
        if not isinstance(txs, list) or not txs:
            raise RuntimeError(f"activation block {tip2} has no txs")
        last = txs[-1]
        hogex = last["txid"] if isinstance(last, dict) else last
        print(f"MWEB_ACTIVATION_HEIGHT={activation} hogex_txid={hogex} fields={bip}")
        return activation
