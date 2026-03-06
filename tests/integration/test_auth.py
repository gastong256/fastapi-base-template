from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from __PROJECT_SLUG__.core.config import get_settings
from __PROJECT_SLUG__.main import create_app


@pytest.fixture
def auth_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_AUTH_ENABLED", "true")
    monkeypatch.setenv("APP_AUTH_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("APP_AUTH_ADMIN_PASSWORD", "super-secret-password")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        yield client

    get_settings.cache_clear()


def test_issue_token_with_form_payload(auth_client: TestClient) -> None:
    response = auth_client.post(
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


def test_issue_token_rejects_invalid_grant_type(auth_client: TestClient) -> None:
    response = auth_client.post(
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
