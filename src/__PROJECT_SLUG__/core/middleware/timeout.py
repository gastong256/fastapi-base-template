from __future__ import annotations

import asyncio
from collections.abc import Iterable
import uuid

import structlog.contextvars
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class RequestTimeoutMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        timeout_seconds: int,
        exempt_paths: Iterable[str],
    ) -> None:
        self.app = app
        self.timeout_seconds = timeout_seconds
        self.exempt_paths = set(exempt_paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self.exempt_paths:
            await self.app(scope, receive, send)
            return

        try:
            await asyncio.wait_for(
                self.app(scope, receive, send),
                timeout=self.timeout_seconds,
            )
        except TimeoutError:
            request_id = str(structlog.contextvars.get_contextvars().get("request_id", str(uuid.uuid4())))
            response = JSONResponse(
                status_code=504,
                content={
                    "error": {
                        "code": "REQUEST_TIMEOUT",
                        "message": "Request processing exceeded timeout.",
                        "request_id": request_id,
                    }
                },
            )
            await response(scope, receive, send)
