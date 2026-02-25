from __future__ import annotations

import uuid

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

log = structlog.get_logger()


def _request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID", str(uuid.uuid4()))


def _envelope(code: str, message: str, request_id: str) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        rid = _request_id(request)
        log.warning("validation_error", request_id=rid, errors=exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope("VALIDATION_ERROR", "Request validation failed.", rid),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        rid = _request_id(request)
        log.warning(
            "http_exception",
            request_id=rid,
            status_code=exc.status_code,
            detail=exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(f"HTTP_{exc.status_code}", str(exc.detail), rid),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        rid = _request_id(request)
        log.exception("unhandled_exception", request_id=rid)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("INTERNAL_ERROR", "An unexpected error occurred.", rid),
        )
