from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.security import SecurityScopes

from __PROJECT_SLUG__.core.config import get_settings
from __PROJECT_SLUG__.core.security.auth import (
    authenticate_admin_user,
    create_access_token,
    decode_access_token,
    get_current_principal,
)


def _set_auth_env(monkeypatch: pytest.MonkeyPatch, *, enabled: bool = True) -> None:
    monkeypatch.setenv("APP_AUTH_ENABLED", str(enabled).lower())
    monkeypatch.setenv("APP_AUTH_JWT_SECRET", "x" * 48)
    monkeypatch.setenv("APP_AUTH_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("APP_AUTH_ADMIN_PASSWORD", "secret-password")
    monkeypatch.setenv("APP_AUTH_ADMIN_SCOPES", "items:read,items:write")
    monkeypatch.setenv("APP_AUTH_ISSUER", "test-service")
    monkeypatch.setenv("APP_AUTH_AUDIENCE", "test-clients")
    get_settings.cache_clear()


def _clear_auth_cache() -> None:
    get_settings.cache_clear()


def test_authenticate_admin_user(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_auth_env(monkeypatch)
    try:
        assert authenticate_admin_user("admin", "secret-password")
        assert not authenticate_admin_user("admin", "bad-password")
        assert not authenticate_admin_user("other", "secret-password")
    finally:
        _clear_auth_cache()


def test_create_and_decode_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_auth_env(monkeypatch)
    try:
        token, expires_in = create_access_token("admin", ["items:write"])
        payload = decode_access_token(token)
        assert expires_in > 0
        assert payload["sub"] == "admin"
        assert payload["scopes"] == ["items:write"]
    finally:
        _clear_auth_cache()


async def test_get_current_principal_bypasses_when_auth_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_auth_env(monkeypatch, enabled=False)
    try:
        principal = await get_current_principal(SecurityScopes(scopes=["items:write"]), token=None)
        assert principal.username == "local-dev"
        assert "items:write" in principal.scopes
    finally:
        _clear_auth_cache()


async def test_get_current_principal_rejects_missing_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_auth_env(monkeypatch, enabled=True)
    try:
        token, _ = create_access_token("admin", ["items:read"])
        with pytest.raises(HTTPException) as exc:
            await get_current_principal(SecurityScopes(scopes=["items:write"]), token=token)
        assert exc.value.status_code == 403
    finally:
        _clear_auth_cache()
