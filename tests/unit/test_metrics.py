from __future__ import annotations

from starlette.types import Message, Receive, Scope, Send

from __PROJECT_SLUG__.core.metrics import PROMETHEUS_AVAILABLE
from __PROJECT_SLUG__.core.metrics.http import MetricsMiddleware, metrics_endpoint


async def test_metrics_middleware_allows_http_response_passthrough() -> None:
    sent_messages: list[Message] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})

    middleware = MetricsMiddleware(app, metrics_path="/metrics")

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent_messages.append(message)

    scope: Scope = {
        "type": "http",
        "path": "/unit-metrics-probe",
        "method": "GET",
        "headers": [],
    }

    await middleware(scope, receive, send)

    assert sent_messages[0]["type"] == "http.response.start"
    assert sent_messages[0]["status"] == 200


def test_metrics_endpoint_response_shape() -> None:
    response = metrics_endpoint()

    if not PROMETHEUS_AVAILABLE:
        assert response.status_code == 503
        assert b"METRICS_UNAVAILABLE" in response.body
        return

    assert response.status_code == 200
    assert b"http_server_requests_total" in response.body
