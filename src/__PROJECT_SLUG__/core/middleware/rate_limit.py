from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
import time
from typing import Protocol
import uuid

import structlog
import structlog.contextvars
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

log = structlog.get_logger()


@dataclass(slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class RateLimiter(Protocol):
    async def check(self, key: str) -> RateLimitDecision:
        ...

    async def ping(self) -> None:
        ...

    async def close(self) -> None:
        ...


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str, now: float | None = None) -> RateLimitDecision:
        current = now if now is not None else time.monotonic()
        cutoff = current - self.window_seconds

        async with self._lock:
            queue = self._events.setdefault(key, deque())
            while queue and queue[0] <= cutoff:
                queue.popleft()

            if len(queue) >= self.max_requests:
                retry_after = max(1, int((queue[0] + self.window_seconds) - current))
                return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)

            queue.append(current)
            return RateLimitDecision(allowed=True)

    async def allow(self, key: str, now: float | None = None) -> bool:
        return (await self.check(key=key, now=now)).allowed

    async def close(self) -> None:
        return None

    async def ping(self) -> None:
        return None


class RedisFixedWindowRateLimiter:
    def __init__(
        self,
        *,
        max_requests: int,
        window_seconds: int,
        redis_url: str,
        key_prefix: str,
        redis_client: object | None = None,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
        self._redis = redis_client or self._build_client(redis_url)

    @staticmethod
    def _build_client(redis_url: str) -> object:
        try:
            from redis import asyncio as redis_asyncio  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "Redis rate limiter backend requires 'redis' dependency. "
                "Install it with: poetry add redis"
            ) from exc
        return redis_asyncio.from_url(redis_url, encoding="utf-8", decode_responses=True)

    def _window_key(self, key: str, now: float) -> str:
        bucket = int(now // self.window_seconds)
        return f"{self.key_prefix}:{bucket}:{key}"

    def _retry_after_seconds(self, now: float) -> int:
        remaining = self.window_seconds - (int(now) % self.window_seconds)
        return remaining if remaining > 0 else 1

    async def check(self, key: str) -> RateLimitDecision:
        now = time.time()
        window_key = self._window_key(key, now)

        count = await self._redis.incr(window_key)
        if count == 1:
            await self._redis.expire(window_key, self.window_seconds * 2)

        if count > self.max_requests:
            return RateLimitDecision(
                allowed=False,
                retry_after_seconds=self._retry_after_seconds(now),
            )

        return RateLimitDecision(allowed=True)

    async def close(self) -> None:
        close = getattr(self._redis, "aclose", None)
        if callable(close):
            await close()

    async def ping(self) -> None:
        await self._redis.ping()


def build_rate_limiter(
    *,
    backend: str,
    max_requests: int,
    window_seconds: int,
    redis_url: str,
    redis_prefix: str,
) -> RateLimiter:
    if backend == "memory":
        return SlidingWindowRateLimiter(max_requests=max_requests, window_seconds=window_seconds)
    if backend == "redis":
        return RedisFixedWindowRateLimiter(
            max_requests=max_requests,
            window_seconds=window_seconds,
            redis_url=redis_url,
            key_prefix=redis_prefix,
        )
    raise ValueError(f"Unsupported rate limit backend: {backend}")


def resolve_client_ip(headers: Headers, scope: Scope, trust_x_forwarded_for: bool) -> str:
    if trust_x_forwarded_for:
        forwarded_for = headers.get("X-Forwarded-For")
        if forwarded_for:
            first_hop = forwarded_for.split(",")[0].strip()
            if first_hop:
                return first_hop

    client = scope.get("client")
    return client[0] if client else "unknown"


class RateLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        limiter: RateLimiter,
        exempt_paths: Iterable[str],
        fail_open: bool = True,
        trust_x_forwarded_for: bool = False,
    ) -> None:
        self.app = app
        self.limiter = limiter
        self.exempt_paths = set(exempt_paths)
        self.fail_open = fail_open
        self.trust_x_forwarded_for = trust_x_forwarded_for

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self.exempt_paths:
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        tenant_id = headers.get("X-Tenant-ID", "public")
        client_ip = resolve_client_ip(headers, scope, self.trust_x_forwarded_for)
        key = f"{client_ip}:{tenant_id}:{path}"

        try:
            decision = await self.limiter.check(key)
        except Exception:
            if self.fail_open:
                log.exception("rate_limit_backend_failed_open", path=path, client_ip=client_ip)
                await self.app(scope, receive, send)
                return
            request_id = str(structlog.contextvars.get_contextvars().get("request_id", str(uuid.uuid4())))
            unavailable = JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "code": "RATE_LIMIT_UNAVAILABLE",
                        "message": "Rate limiting backend unavailable.",
                        "request_id": request_id,
                    }
                },
            )
            await unavailable(scope, receive, send)
            return

        if decision.allowed:
            await self.app(scope, receive, send)
            return

        request_id = str(structlog.contextvars.get_contextvars().get("request_id", str(uuid.uuid4())))
        retry_after = decision.retry_after_seconds if decision.retry_after_seconds > 0 else 1
        limited = JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Rate limit exceeded. Retry later.",
                    "request_id": request_id,
                }
            },
            headers={"Retry-After": str(retry_after)},
        )
        await limited(scope, receive, send)
