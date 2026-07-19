"""Wallet RPC helpers (create/load, addresses, mining batches)."""

from __future__ import annotations

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
        if not isinstance(result, list):
            raise RuntimeError(f"generatetoaddress returned non-list: {type(result)}")
        hashes.extend(str(h) for h in result)
        remaining -= batch
    return hashes


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
