from __future__ import annotations

from collections.abc import Iterable
import uuid

import structlog.contextvars
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyTooLarge(Exception):
    pass


class RequestBodyLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        max_body_bytes: int,
        exempt_paths: Iterable[str],
    ) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.exempt_paths = set(exempt_paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self.exempt_paths:
            await self.app(scope, receive, send)
            return

        total_bytes = 0

        async def receive_wrapper() -> Message:
            nonlocal total_bytes
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                total_bytes += len(body)
                if total_bytes > self.max_body_bytes:
                    raise RequestBodyTooLarge
            return message

        try:
            await self.app(scope, receive_wrapper, send)
        except RequestBodyTooLarge:
            request_id = str(structlog.contextvars.get_contextvars().get("request_id", str(uuid.uuid4())))
            response = JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "REQUEST_BODY_TOO_LARGE",
                        "message": "Request body exceeds configured limit.",
                        "request_id": request_id,
                    }
                },
            )
            await response(scope, receive, send)
