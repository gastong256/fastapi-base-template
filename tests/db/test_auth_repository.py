from __future__ import annotations

from __PROJECT_SLUG__.api.v1.features.auth import service as auth_service
from __PROJECT_SLUG__.api.v1.features.auth.repository import AuthRepository
from __PROJECT_SLUG__.core.db import db_manager


async def test_create_and_authenticate_database_user() -> None:
    async with db_manager.session_factory() as session:
        repo = AuthRepository(session)
        created = await repo.create_user(
            username="db-admin",
            password_hash=auth_service.hash_password("super-secret"),
            scopes_csv=auth_service.scopes_to_csv(["items:read", "items:write"]),
            is_active=True,
        )

    async with db_manager.session_factory() as session:
        principal = await auth_service.authenticate_database_user(
            username="db-admin",
            password="super-secret",
            session=session,
        )

    assert principal is not None
    assert principal.user_id == created.id
    assert principal.username == "db-admin"
    assert set(principal.scopes) == {"items:read", "items:write"}


async def test_refresh_token_rotation_and_revocation_flow() -> None:
    async with db_manager.session_factory() as session:
        repo = AuthRepository(session)
        user = await repo.create_user(
            username="rotator",
            password_hash=auth_service.hash_password("super-secret"),
            scopes_csv=auth_service.scopes_to_csv(["items:read"]),
            is_active=True,
        )

    async with db_manager.session_factory() as session:
        refresh_token, _ = await auth_service.issue_refresh_token(
            session=session,
            user_id=user.id,
            expires_minutes=60,
        )

    async with db_manager.session_factory() as session:
        rotated = await auth_service.rotate_refresh_token(
            session=session,
            refresh_token=refresh_token,
            expires_minutes=60,
        )

    assert rotated is not None
    principal, new_refresh_token, refresh_expires_in = rotated
    assert principal.username == "rotator"
    assert new_refresh_token != refresh_token
    assert refresh_expires_in > 0

    async with db_manager.session_factory() as session:
        revoked = await auth_service.revoke_refresh_token(
            session=session,
            refresh_token=new_refresh_token,
        )

    assert revoked is True
