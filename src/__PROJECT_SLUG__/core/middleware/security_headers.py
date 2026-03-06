from __future__ import annotations

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SecurityHeadersMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        csp: str,
        hsts_enabled: bool,
        hsts_seconds: int,
    ) -> None:
        self.app = app
        self.csp = csp
        self.hsts_enabled = hsts_enabled
        self.hsts_seconds = hsts_seconds

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Referrer-Policy", "no-referrer")
                headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
                headers.setdefault("Content-Security-Policy", self.csp)
                if self.hsts_enabled:
                    headers.setdefault(
                        "Strict-Transport-Security",
                        f"max-age={self.hsts_seconds}; includeSubDomains; preload",
                    )
            await send(message)

        await self.app(scope, receive, send_with_security_headers)
