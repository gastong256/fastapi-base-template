from __future__ import annotations

import asyncio
import json
from typing import Any

from starlette.types import Message, Receive, Scope, Send

from __PROJECT_SLUG__.core.middleware.body_size import RequestBodyLimitMiddleware
from __PROJECT_SLUG__.core.middleware.timeout import RequestTimeoutMiddleware


async def _collect_response(
    app,
    scope: Scope,
    receive_messages: list[Message],
) -> tuple[int, dict[str, Any]]:
    sent: list[Message] = []

    queue = list(receive_messages)

    async def receive() -> Message:
        if queue:
            return queue.pop(0)
        await asyncio.sleep(0)
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent.append(message)

    await app(scope, receive, send)

    start = next(msg for msg in sent if msg["type"] == "http.response.start")
    body = next(msg for msg in sent if msg["type"] == "http.response.body")
    status = int(start["status"])
    payload = json.loads(body.get("body", b"{}").decode() or "{}")
    return status, payload


async def test_request_timeout_middleware_returns_504() -> None:
    async def slow_app(scope: Scope, receive: Receive, send: Send) -> None:
        await asyncio.sleep(0.05)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b'{"ok":true}', "more_body": False})

    middleware = RequestTimeoutMiddleware(slow_app, timeout_seconds=0, exempt_paths=[])
    scope: Scope = {
        "type": "http",
        "path": "/items",
        "method": "POST",
        "headers": [],
    }

    status, body = await _collect_response(
        middleware,
        scope,
        [{"type": "http.request", "body": b"{}", "more_body": False}],
    )

    assert status == 504
    assert body["error"]["code"] == "REQUEST_TIMEOUT"


async def test_request_timeout_middleware_exempt_path_passthrough() -> None:
    async def fast_app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b'{"ok":true}', "more_body": False})

    middleware = RequestTimeoutMiddleware(fast_app, timeout_seconds=0, exempt_paths=["/health"])
    scope: Scope = {
        "type": "http",
        "path": "/health",
        "method": "GET",
        "headers": [],
    }

    status, _ = await _collect_response(
        middleware,
        scope,
        [{"type": "http.request", "body": b"", "more_body": False}],
    )

    assert status == 200


async def test_request_body_limit_middleware_returns_413() -> None:
    async def read_body_app(scope: Scope, receive: Receive, send: Send) -> None:
        while True:
            message = await receive()
            if message["type"] != "http.request":
                continue
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b'{"ok":true}', "more_body": False})

    middleware = RequestBodyLimitMiddleware(read_body_app, max_body_bytes=4, exempt_paths=[])
    scope: Scope = {
        "type": "http",
        "path": "/upload",
        "method": "POST",
        "headers": [],
    }

    status, body = await _collect_response(
        middleware,
        scope,
        [
            {"type": "http.request", "body": b"123", "more_body": True},
            {"type": "http.request", "body": b"45", "more_body": False},
        ],
    )

    assert status == 413
    assert body["error"]["code"] == "REQUEST_BODY_TOO_LARGE"


async def test_request_body_limit_middleware_allows_small_payload() -> None:
    async def read_body_app(scope: Scope, receive: Receive, send: Send) -> None:
        while True:
            message = await receive()
            if message["type"] != "http.request":
                continue
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 201, "headers": []})
        await send({"type": "http.response.body", "body": b'{"ok":true}', "more_body": False})

    middleware = RequestBodyLimitMiddleware(read_body_app, max_body_bytes=16, exempt_paths=[])
    scope: Scope = {
        "type": "http",
        "path": "/upload",
        "method": "POST",
        "headers": [],
    }

    status, _ = await _collect_response(
        middleware,
        scope,
        [{"type": "http.request", "body": b"1234", "more_body": False}],
    )

    assert status == 201
