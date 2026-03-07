from __future__ import annotations

import httpx
import pytest

from __PROJECT_SLUG__.core.config import get_settings
from __PROJECT_SLUG__.main import create_app


async def test_docs_available_by_default(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/docs")).status_code == 200
    assert (await client.get("/api/redoc")).status_code == 200
    assert (await client.get("/api/openapi.json")).status_code == 200


async def test_docs_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_API_DOCS_ENABLED", "false")
    get_settings.cache_clear()

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as test_client:
            assert (await test_client.get("/api/docs")).status_code == 404
            assert (await test_client.get("/api/redoc")).status_code == 404
            assert (await test_client.get("/api/openapi.json")).status_code == 404

    get_settings.cache_clear()
