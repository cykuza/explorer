"""Shared helpers for tests (unit + integration)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from explorer.rpc import RpcClient, RpcError


def rpc_root_url(url: str) -> str:
    """Strip ``/wallet/<name>`` suffix if present."""
    base = url.rstrip("/")
    if "/wallet/" in base:
        return base.split("/wallet/")[0]
    return base


def wallet_rpc_url(url: str, name: str) -> str:
    return f"{rpc_root_url(url)}/wallet/{name}"


async def ensure_wallet(rpc: RpcClient, name: str = "testwallet") -> None:
    """Create or load a wallet for mining/sending; no-op if already loaded.

    Uses the node root RPC endpoint (not ``/wallet/...``) so it works even when
    multiple wallets are loaded.
    """
    root = RpcClient(rpc_root_url(rpc.url), rpc.auth[0], rpc.auth[1])
    try:
        try:
            wallets = await root.call("listwallets")
            if isinstance(wallets, list) and name in wallets:
                return
        except RpcError:
            pass

        try:
            await root.call("loadwallet", name)
            return
        except RpcError as exc:
            if "already loaded" in exc.message.lower():
                return
            if exc.code not in (-18, -4):
                pass

        try:
            await root.call("createwallet", name)
        except RpcError as exc:
            if "already exists" in exc.message.lower() or "already loaded" in exc.message.lower():
                try:
                    await root.call("loadwallet", name)
                except RpcError as load_exc:
                    if "already loaded" not in load_exc.message.lower():
                        raise
                return
            raise
    finally:
        await root.aclose()


async def mine_to(rpc: RpcClient, address: str, n: int) -> list[str]:
    """Mine ``n`` blocks to ``address``, in batches to avoid RPC timeouts."""
    hashes: list[str] = []
    remaining = n
    while remaining > 0:
        batch = min(25, remaining)
        result = await rpc.call("generatetoaddress", batch, address)
        assert isinstance(result, list)
        hashes.extend(str(h) for h in result)
        remaining -= batch
    return hashes


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


def _softfork_entry(info: dict[str, Any], name: str) -> dict[str, Any] | None:
    softforks = info.get("softforks") or info.get("bip9_softforks") or {}
    if not isinstance(softforks, dict):
        return None
    entry = softforks.get(name)
    return entry if isinstance(entry, dict) else None


def _softfork_bip(entry: dict[str, Any]) -> dict[str, Any]:
    bip = entry.get("bip8") or entry.get("bip9") or {}
    return bip if isinstance(bip, dict) else {}


def _softfork_active(info: dict[str, Any], name: str) -> bool:
    entry = _softfork_entry(info, name)
    if entry is None:
        return False
    if entry.get("active") is True:
        return True
    status = entry.get("status")
    if isinstance(status, str) and status.lower() == "active":
        return True
    bip = _softfork_bip(entry)
    bip_status = bip.get("status")
    return isinstance(bip_status, str) and bip_status.lower() == "active"


def _miner_confirmation_window(info: dict[str, Any]) -> int:
    """BIP period from any softfork ``statistics.period`` (same nMinerConfirmationWindow)."""
    softforks = info.get("softforks") or {}
    if not isinstance(softforks, dict):
        raise RuntimeError("getblockchaininfo.softforks missing")
    for entry in softforks.values():
        if not isinstance(entry, dict):
            continue
        bip = _softfork_bip(entry)
        stats = bip.get("statistics") or {}
        if isinstance(stats, dict) and stats.get("period") is not None:
            return int(stats["period"])
    raise RuntimeError(
        "cannot derive miner confirmation window: no softfork statistics.period",
    )


def predict_mweb_activation_height(info: dict[str, Any]) -> int | None:
    """Return MWEB activation height from ``getblockchaininfo``, or None if still defined.

    Uses ``softforks.mweb`` status/since/height plus ``statistics.period`` from any
    deployment (testdummy while mweb has no stats). Does not hardcode 430/431/432.
    """
    mweb = _softfork_entry(info, "mweb") or _softfork_entry(info, "MWEB")
    if mweb is None:
        raise RuntimeError("mweb softfork missing from getblockchaininfo")
    bip = _softfork_bip(mweb)
    status = str(bip.get("status") or mweb.get("status") or "").lower()

    if mweb.get("active") is True or status == "active":
        if mweb.get("height") is not None:
            return int(mweb["height"])
        if bip.get("since") is not None:
            return int(bip["since"])
        raise RuntimeError(f"mweb active but no height/since: {mweb}")

    if status == "defined":
        return None

    period = _miner_confirmation_window(info)
    if status == "locked_in":
        # ACTIVE begins at the next period boundary after locked_in.since.
        return int(bip["since"]) + period
    if status == "started":
        # Height-based timeout_height==start_height forces LOCKED_IN at the end of
        # this period, then ACTIVE after one more period.
        return int(bip["since"]) + 2 * period
    raise RuntimeError(f"unhandled mweb softfork status {status!r}: {mweb}")


async def mweb_address(rpc: RpcClient) -> str:
    """Return a new MWEB address (tries address_type variants the node accepts)."""
    attempts: list[tuple[Any, ...]] = [
        ("mweb", "mweb"),
        ("", "mweb"),
        ("mweb",),
    ]
    last_exc: RpcError | None = None
    for args in attempts:
        try:
            addr = await rpc.call("getnewaddress", *args)
            return str(addr)
        except RpcError as exc:
            last_exc = exc
            continue
    try:
        help_text = str(await rpc.call("help", "getnewaddress"))
        print(f"getnewaddress help:\n{help_text}")
    except RpcError:
        pass
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("getnewaddress mweb variants all failed")


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
        mweb = _softfork_entry(info, "mweb") or _softfork_entry(info, "MWEB")
        assert mweb is not None
        bip = _softfork_bip(mweb)

        activation = predict_mweb_activation_height(info)
        if activation is None:
            await mine_to(rpc, mine_address, 25)
            continue

        # Activation block already on chain.
        if tip >= activation and (_softfork_active(info, "mweb") or _softfork_active(info, "MWEB")):
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
        if not (_softfork_active(info2, "mweb") or _softfork_active(info2, "MWEB")):
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
