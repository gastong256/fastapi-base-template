from __future__ import annotations

from urllib.parse import parse_qs
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError

from __PROJECT_SLUG__.api.v1.features.auth.schemas import PasswordGrantRequest, TokenResponse
from __PROJECT_SLUG__.core.config import get_settings
from __PROJECT_SLUG__.core.security.auth import authenticate_admin_user, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


async def parse_password_grant_request(request: Request) -> PasswordGrantRequest:
    content_type = request.headers.get("content-type", "").lower()

    try:
        if content_type.startswith("application/json"):
            payload = await request.json()
            if not isinstance(payload, dict):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid token request payload.",
                )
            return PasswordGrantRequest.model_validate(payload)

        body = (await request.body()).decode()
        parsed = {
            key: values[0] if values else ""
            for key, values in parse_qs(body, keep_blank_values=True).items()
        }
        return PasswordGrantRequest.model_validate(parsed)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid token request payload.",
        ) from exc


@router.post("/token", response_model=TokenResponse)
async def issue_access_token(
    form_data: Annotated[PasswordGrantRequest, Depends(parse_password_grant_request)],
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

    if not authenticate_admin_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin_scopes = set(settings.auth_admin_scopes)
    requested_scopes = {scope for scope in form_data.scope.split() if scope}

    if requested_scopes and not requested_scopes.issubset(admin_scopes):
        missing = sorted(requested_scopes.difference(admin_scopes))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested scopes are not allowed: {', '.join(missing)}",
        )

    token_scopes = sorted(requested_scopes) if requested_scopes else sorted(admin_scopes)
    access_token, expires_in = create_access_token(form_data.username, token_scopes)
    return TokenResponse(access_token=access_token, expires_in=expires_in)
