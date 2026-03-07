from __future__ import annotations

import time

from fastapi import Response
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

try:  # pragma: no cover - availability depends on runtime environment
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

    PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover - handled explicitly by fallback behavior
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    PROMETHEUS_AVAILABLE = False


if PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter(
        "http_server_requests_total",
        "Total HTTP requests processed by the application.",
        labelnames=("method", "path", "status_code"),
    )
    REQUEST_DURATION = Histogram(
        "http_server_request_duration_seconds",
        "HTTP request latency in seconds.",
        labelnames=("method", "path"),
    )


def metrics_endpoint() -> Response:
    if not PROMETHEUS_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "METRICS_UNAVAILABLE",
                    "message": "prometheus_client is not installed.",
                    "request_id": "n/a",
                }
            },
        )
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _normalize_path(scope: Scope) -> str:
    route = scope.get("route")
    route_path = getattr(route, "path", None)
    if isinstance(route_path, str) and route_path:
        return route_path
    return str(scope.get("path", "unknown"))


class MetricsMiddleware:
    def __init__(self, app: ASGIApp, *, metrics_path: str) -> None:
        self.app = app
        self.metrics_path = metrics_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not PROMETHEUS_AVAILABLE:
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path", ""))
        if path == self.metrics_path:
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        method = str(scope.get("method", "UNKNOWN"))
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = max(time.perf_counter() - start, 0.0)
            normalized_path = _normalize_path(scope)
            REQUEST_COUNT.labels(
                method=method, path=normalized_path, status_code=str(status_code)
            ).inc()
            REQUEST_DURATION.labels(method=method, path=normalized_path).observe(duration)
