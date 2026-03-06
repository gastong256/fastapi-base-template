from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from __PROJECT_SLUG__.core.config import get_settings
from __PROJECT_SLUG__.core.db import get_db_session
from __PROJECT_SLUG__.core.readiness import register_readiness_check
from __PROJECT_SLUG__.main import create_app


@pytest_asyncio.fixture
async def auth_client(monkeypatch: pytest.MonkeyPatch) -> httpx.AsyncClient:
    monkeypatch.setenv("APP_AUTH_ENABLED", "true")
    monkeypatch.setenv("APP_AUTH_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("APP_AUTH_ADMIN_PASSWORD", "super-secret-password")
    get_settings.cache_clear()

    app = create_app()

    async def _no_db_session():
        yield None

    async def _database_readiness_noop(_app: object) -> None:
        return None

    app.dependency_overrides[get_db_session] = _no_db_session
    register_readiness_check(app, "database", _database_readiness_noop)

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client

    get_settings.cache_clear()


@pytest_asyncio.fixture
async def auth_dbmode_client(monkeypatch: pytest.MonkeyPatch) -> httpx.AsyncClient:
    monkeypatch.setenv("APP_AUTH_ENABLED", "true")
    monkeypatch.setenv("APP_AUTH_USE_DATABASE", "true")
    monkeypatch.setenv("APP_AUTH_REFRESH_TOKEN_ENABLED", "true")
    monkeypatch.setenv("APP_AUTH_JWT_SECRET", "x" * 40)
    get_settings.cache_clear()

    app = create_app()

    async def _dummy_db_session():
        yield object()

    async def _database_readiness_noop(_app: object) -> None:
        return None

    app.dependency_overrides[get_db_session] = _dummy_db_session
    register_readiness_check(app, "database", _database_readiness_noop)

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client

    get_settings.cache_clear()


async def test_issue_token_with_form_payload(auth_client: httpx.AsyncClient) -> None:
    response = await auth_client.post(
        "/api/v1/auth/token",
        data={
            "username": "admin",
            "password": "super-secret-password",
            "scope": "items:write",
            "grant_type": "password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["expires_in"] > 0


async def test_issue_token_rejects_invalid_grant_type(auth_client: httpx.AsyncClient) -> None:
    response = await auth_client.post(
        "/api/v1/auth/token",
        data={
            "username": "admin",
            "password": "super-secret-password",
            "grant_type": "client_credentials",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "HTTP_400"


async def test_issue_token_rejects_malformed_json_payload(auth_client: httpx.AsyncClient) -> None:
    response = await auth_client.post(
        "/api/v1/auth/token",
        content="{not json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "HTTP_422"


async def test_issue_token_rejects_non_utf8_form_payload(auth_client: httpx.AsyncClient) -> None:
    response = await auth_client.post(
        "/api/v1/auth/token",
        content=b"\x80\x80\x80",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "HTTP_422"


async def test_revoke_endpoint_is_idempotent(
    auth_dbmode_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _always_not_found(*, session: object, refresh_token: str) -> bool:
        assert refresh_token == "nope"
        return False

    monkeypatch.setattr(
        "__PROJECT_SLUG__.api.v1.features.auth.router.service.revoke_refresh_token",
        _always_not_found,
    )

    response = await auth_dbmode_client.post(
        "/api/v1/auth/revoke",
        json={"refresh_token": "nope"},
    )

    assert response.status_code == 204
