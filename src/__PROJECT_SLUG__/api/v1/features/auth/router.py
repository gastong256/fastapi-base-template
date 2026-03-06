from __future__ import annotations

from json import JSONDecodeError
from urllib.parse import parse_qs
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from __PROJECT_SLUG__.api.v1.features.auth import service
from __PROJECT_SLUG__.api.v1.features.auth.schemas import (
    PasswordGrantRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from __PROJECT_SLUG__.core.config import get_settings
from __PROJECT_SLUG__.core.db import get_db_session
from __PROJECT_SLUG__.core.security.auth import authenticate_admin_user, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


async def parse_password_grant_request(request: Request) -> PasswordGrantRequest:
    content_type = request.headers.get("content-type", "").lower()

    try:
        if content_type.startswith("application/json"):
            payload = await request.json()
            if not isinstance(payload, dict):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Invalid token request payload.",
                )
            return PasswordGrantRequest.model_validate(payload)

        body = (await request.body()).decode()
        parsed = {
            key: values[0] if values else ""
            for key, values in parse_qs(body, keep_blank_values=True).items()
        }
        return PasswordGrantRequest.model_validate(parsed)
    except (ValidationError, JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid token request payload.",
        ) from exc


@router.post("/token", response_model=TokenResponse)
async def issue_access_token(
    form_data: Annotated[PasswordGrantRequest, Depends(parse_password_grant_request)],
    db_session: Annotated[AsyncSession | None, Depends(get_db_session)],
) -> TokenResponse:
    settings = get_settings()

    if not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication is disabled for this environment.",
        )

    if form_data.grant_type and form_data.grant_type != "password":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported grant_type. Expected 'password'.",
        )

    principal_username: str
    principal_scopes: set[str]
    principal_subject: str | None = None
    principal_user_id = None

    if settings.auth_use_database:
        if db_session is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database session is required for database-backed authentication.",
            )
        user = await service.authenticate_database_user(
            username=form_data.username,
            password=form_data.password,
            session=db_session,
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        principal_username = user.username
        principal_scopes = set(user.scopes)
        principal_subject = f"user:{user.user_id}"
        principal_user_id = user.user_id
    else:
        if not authenticate_admin_user(form_data.username, form_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        principal_username = form_data.username
        principal_scopes = set(settings.auth_admin_scopes)

    requested_scopes = {scope for scope in form_data.scope.split() if scope}

    if requested_scopes and not requested_scopes.issubset(principal_scopes):
        missing = sorted(requested_scopes.difference(principal_scopes))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested scopes are not allowed: {', '.join(missing)}",
        )

    token_scopes = sorted(requested_scopes) if requested_scopes else sorted(principal_scopes)
    access_token, expires_in = create_access_token(
        username=principal_username,
        scopes=token_scopes,
        subject=principal_subject,
    )

    refresh_token: str | None = None
    refresh_expires_in: int | None = None
    if (
        settings.auth_use_database
        and settings.auth_refresh_token_enabled
        and db_session is not None
        and principal_user_id is not None
    ):
        refresh_token, refresh_expires_in = await service.issue_refresh_token(
            session=db_session,
            user_id=principal_user_id,
            expires_minutes=settings.auth_refresh_token_expire_minutes,
        )

    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        refresh_token=refresh_token,
        refresh_expires_in=refresh_expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    payload: RefreshTokenRequest,
    db_session: Annotated[AsyncSession | None, Depends(get_db_session)],
) -> TokenResponse:
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication is disabled for this environment.",
        )
    if not settings.auth_use_database:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token flow requires auth_use_database=true.",
        )
    if not settings.auth_refresh_token_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token flow is disabled.",
        )
    if db_session is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database session is required for refresh token flow.",
        )

    rotated = await service.rotate_refresh_token(
        session=db_session,
        refresh_token=payload.refresh_token,
        expires_minutes=settings.auth_refresh_token_expire_minutes,
    )
    if rotated is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    principal, refresh_token, refresh_expires_in = rotated
    access_token, expires_in = create_access_token(
        username=principal.username,
        scopes=principal.scopes,
        subject=f"user:{principal.user_id}",
    )
    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        refresh_token=refresh_token,
        refresh_expires_in=refresh_expires_in,
    )


@router.post("/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_refresh_token(
    payload: RefreshTokenRequest,
    db_session: Annotated[AsyncSession | None, Depends(get_db_session)],
) -> None:
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication is disabled for this environment.",
        )
    if not settings.auth_use_database:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token flow requires auth_use_database=true.",
        )
    if db_session is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database session is required for token revocation.",
        )

    await service.revoke_refresh_token(session=db_session, refresh_token=payload.refresh_token)
