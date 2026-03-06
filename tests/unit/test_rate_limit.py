from __future__ import annotations

from __PROJECT_SLUG__.core.middleware.rate_limit import SlidingWindowRateLimiter


async def test_sliding_window_rate_limiter_enforces_limit() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=10)

    assert await limiter.allow("ip1", now=0.0)
    assert await limiter.allow("ip1", now=1.0)
    assert not await limiter.allow("ip1", now=2.0)


async def test_sliding_window_rate_limiter_allows_after_window() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=10)

    assert await limiter.allow("ip1", now=0.0)
    assert await limiter.allow("ip1", now=1.0)
    assert not await limiter.allow("ip1", now=2.0)
    assert await limiter.allow("ip1", now=12.1)
