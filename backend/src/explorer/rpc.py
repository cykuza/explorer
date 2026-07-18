"""Minimal async JSON-RPC client for Cyberyen Core over HTTP."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import httpx


class RpcError(Exception):
    """JSON-RPC error returned by the node."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"RPC error {code}: {message}")


class RpcHttpError(Exception):
    """Non-JSON or unexpected HTTP failure talking to the RPC endpoint."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"RPC HTTP {status_code}: {detail}")


def _parse_rpc_body(text: str) -> dict[str, Any]:
    """Parse RPC JSON with Decimal for fractional numbers (never float)."""
    value = json.loads(text, parse_float=Decimal)
    if not isinstance(value, dict):
        raise ValueError("RPC response is not a JSON object")
    return value


class RpcClient:
    """Async JSON-RPC 1.0 client (bitcoind-compatible)."""

    def __init__(
        self,
        url: str,
        user: str,
        password: str,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._url = url
        self._auth = (user, password)
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(120.0))
        self._next_id = 1

    @property
    def url(self) -> str:
        return self._url

    @property
    def auth(self) -> tuple[str, str]:
        return self._auth

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> RpcClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def call(self, method: str, *params: Any) -> Any:
        request_id = self._next_id
        self._next_id += 1
        payload = {
            "jsonrpc": "1.0",
            "id": request_id,
            "method": method,
            "params": list(params),
        }
        try:
            response = await self._client.post(
                self._url,
                json=payload,
                auth=self._auth,
            )
        except httpx.HTTPError as exc:
            raise RpcHttpError(0, str(exc)) from exc

        if response.status_code != 200:
            # bitcoind-family nodes often return HTTP 500 with a JSON-RPC error body.
            try:
                body = _parse_rpc_body(response.text)
            except ValueError as exc:
                raise RpcHttpError(response.status_code, response.text) from exc
            error = body.get("error")
            if error is not None:
                raise RpcError(int(error["code"]), str(error["message"]))
            raise RpcHttpError(response.status_code, response.text)

        try:
            body = _parse_rpc_body(response.text)
        except ValueError as exc:
            raise RpcHttpError(response.status_code, "invalid JSON response") from exc

        error = body.get("error")
        if error is not None:
            raise RpcError(int(error["code"]), str(error["message"]))

        return body.get("result")
