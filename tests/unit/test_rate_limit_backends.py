from __future__ import annotations

import pytest
from starlette.datastructures import Headers

from __PROJECT_SLUG__.core.middleware.rate_limit import (
    RedisFixedWindowRateLimiter,
    SlidingWindowRateLimiter,
    build_rate_limit_key,
    build_rate_limiter,
    resolve_client_ip,
)


class FakeRedisClient:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.expire_calls: list[tuple[str, int]] = []
        self.closed = False
        self.ping_called = False

    async def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def expire(self, key: str, seconds: int) -> bool:
        self.expire_calls.append((key, seconds))
        return True

    async def aclose(self) -> None:
        self.closed = True

    async def ping(self) -> bool:
        self.ping_called = True
        return True


async def test_sliding_window_check_returns_retry_after() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=10)

    first = await limiter.check("k1", now=0.0)
    second = await limiter.check("k1", now=2.0)

    assert first.allowed is True
    assert second.allowed is False
    assert second.retry_after_seconds == 8


async def test_redis_fixed_window_enforces_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedisClient()
    limiter = RedisFixedWindowRateLimiter(
        max_requests=2,
        window_seconds=60,
        redis_url="redis://unused",
        key_prefix="svc",
        redis_client=fake_redis,
    )
    monkeypatch.setattr("__PROJECT_SLUG__.core.middleware.rate_limit.time.time", lambda: 125.0)

    first = await limiter.check("ip:tenant:path")
    second = await limiter.check("ip:tenant:path")
    third = await limiter.check("ip:tenant:path")

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.retry_after_seconds == 55
    assert len(fake_redis.expire_calls) == 1


async def test_redis_fixed_window_close_calls_client() -> None:
    fake_redis = FakeRedisClient()
    limiter = RedisFixedWindowRateLimiter(
        max_requests=1,
        window_seconds=60,
        redis_url="redis://unused",
        key_prefix="svc",
        redis_client=fake_redis,
    )

    await limiter.close()

    assert fake_redis.closed is True


async def test_redis_fixed_window_ping_calls_client() -> None:
    fake_redis = FakeRedisClient()
    limiter = RedisFixedWindowRateLimiter(
        max_requests=1,
        window_seconds=60,
        redis_url="redis://unused",
        key_prefix="svc",
        redis_client=fake_redis,
    )

    await limiter.ping()

    assert fake_redis.ping_called is True


def test_build_rate_limiter_memory_backend() -> None:
    limiter = build_rate_limiter(
        backend="memory",
        max_requests=10,
        window_seconds=60,
        memory_max_keys=1000,
        redis_url="redis://localhost:6379/0",
        redis_prefix="svc",
    )

    assert isinstance(limiter, SlidingWindowRateLimiter)


async def test_memory_limiter_ping_is_noop() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=10)
    await limiter.ping()


async def test_sliding_window_evicts_oldest_when_max_keys_reached() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=10, max_keys=2)

    assert (await limiter.check("k1", now=0.0)).allowed is True
    assert (await limiter.check("k2", now=1.0)).allowed is True
    assert (await limiter.check("k3", now=2.0)).allowed is True
    assert (await limiter.check("k1", now=3.0)).allowed is True


def test_build_rate_limit_key_hashes_components() -> None:
    first = build_rate_limit_key(client_ip="10.0.0.1", tenant_id="acme", path="/api/v1/items")
    second = build_rate_limit_key(client_ip="10.0.0.1", tenant_id="acme", path="/api/v1/items")
    third = build_rate_limit_key(client_ip="10.0.0.1", tenant_id="acme", path="/api/v1/other")

    assert first == second
    assert first != third


def test_resolve_client_ip_prefers_forwarded_header_when_trusted() -> None:
    headers = Headers({"X-Forwarded-For": "198.51.100.23, 10.0.0.1"})
    scope = {"client": ("127.0.0.1", 4242)}

    assert resolve_client_ip(headers, scope, trust_x_forwarded_for=True) == "198.51.100.23"


def test_resolve_client_ip_uses_socket_ip_when_untrusted() -> None:
    headers = Headers({"X-Forwarded-For": "198.51.100.23, 10.0.0.1"})
    scope = {"client": ("127.0.0.1", 4242)}

    assert resolve_client_ip(headers, scope, trust_x_forwarded_for=False) == "127.0.0.1"
