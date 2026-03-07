from __future__ import annotations

from datetime import UTC, datetime, timedelta
import secrets
from typing import Annotated, Any
import uuid

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from pydantic import BaseModel, Field

from __PROJECT_SLUG__.core.config import get_settings

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    scopes={
        "items:read": "Read items",
        "items:write": "Create and mutate items",
    },
    auto_error=False,
)


class AuthPrincipal(BaseModel):
    username: str
    scopes: list[str] = Field(default_factory=list)


def authenticate_admin_user(username: str, password: str) -> bool:
    settings = get_settings()
    return secrets.compare_digest(
        username, settings.auth_admin_username
    ) and secrets.compare_digest(
        password,
        settings.auth_admin_password,
    )


def create_access_token(
    *,
    username: str,
    scopes: list[str],
    subject: str | None = None,
) -> tuple[str, int]:
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.auth_access_token_expire_minutes)
    expires_at = datetime.now(UTC) + expires_delta
    payload = {
        "sub": subject or username,
        "username": username,
        "scopes": scopes,
        "typ": "access",
        "jti": str(uuid.uuid4()),
        "iss": settings.auth_issuer,
        "aud": settings.auth_audience,
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.auth_jwt_secret, algorithm=settings.auth_jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    secrets_to_try = [settings.auth_jwt_secret, *settings.auth_jwt_additional_secrets]
    for secret in secrets_to_try:
        try:
            return jwt.decode(
                token,
                secret,
                algorithms=[settings.auth_jwt_algorithm],
                audience=settings.auth_audience,
                issuer=settings.auth_issuer,
            )
        except jwt.InvalidTokenError:
            continue
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_principal(
    security_scopes: SecurityScopes,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> AuthPrincipal:
    settings = get_settings()

    if not settings.auth_enabled:
        return AuthPrincipal(
            username="local-dev",
            scopes=list(settings.auth_admin_scopes),
        )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    token_type = str(payload.get("typ", ""))
    if token_type and token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token type.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = str(payload.get("username", payload.get("sub", "")))
    token_scopes = payload.get("scopes", [])

    if not isinstance(token_scopes, list) or not all(
        isinstance(scope, str) for scope in token_scopes
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token scopes.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    missing_scopes = [scope for scope in security_scopes.scopes if scope not in token_scopes]
    if missing_scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required scopes: {', '.join(missing_scopes)}",
        )

    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthPrincipal(username=username, scopes=list(token_scopes))


def require_scopes(scopes: list[str]):
    async def dependency(
        principal: AuthPrincipal = Security(get_current_principal, scopes=scopes),
    ) -> AuthPrincipal:
        return principal

    return dependency
