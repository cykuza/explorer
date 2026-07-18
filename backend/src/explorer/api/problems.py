"""RFC 7807 problem+json error responses."""

from __future__ import annotations

from typing import Any, NoReturn

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_CONTENT_TYPE = "application/problem+json"


def problem_body(
    *,
    status: int,
    title: str,
    detail: str,
    type_uri: str = "about:blank",
) -> dict[str, Any]:
    return {
        "type": type_uri,
        "title": title,
        "status": status,
        "detail": detail,
    }


def problem_response(
    *,
    status: int,
    title: str,
    detail: str,
    type_uri: str = "about:blank",
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=problem_body(status=status, title=title, detail=detail, type_uri=type_uri),
        media_type=PROBLEM_CONTENT_TYPE,
    )


def raise_problem(status: int, title: str, detail: str) -> NoReturn:
    """Raise Starlette HTTPException carrying problem fields in ``detail`` dict."""
    raise StarletteHTTPException(
        status_code=status,
        detail={"title": title, "detail": detail},  # type: ignore[arg-type]
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        title = "HTTP Error"
        detail_text = str(exc.detail)
        if isinstance(exc.detail, dict):
            title = str(exc.detail.get("title", title))
            detail_text = str(exc.detail.get("detail", detail_text))
        elif exc.status_code == 404:
            title = "Not Found"
        elif exc.status_code == 503:
            title = "Service Unavailable"
        return problem_response(status=exc.status_code, title=title, detail=detail_text)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = exc.errors()
        parts: list[str] = []
        for err in errors:
            loc = ".".join(str(x) for x in err.get("loc", ()))
            msg = str(err.get("msg", "invalid"))
            parts.append(f"{loc}: {msg}" if loc else msg)
        detail = "; ".join(parts) if parts else "Request validation failed"
        return problem_response(
            status=422,
            title="Unprocessable Entity",
            detail=detail,
        )
