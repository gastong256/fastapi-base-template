from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from __PROJECT_SLUG__.api.v1.features.auth import service as auth_service
from __PROJECT_SLUG__.api.v1.features.auth.models import User
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


async def test_refresh_token_rotation_is_single_use_under_concurrency() -> None:
    async with db_manager.session_factory() as session:
        repo = AuthRepository(session)
        user = await repo.create_user(
            username="single-use",
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

    async def rotate_once() -> tuple[auth_service.AuthenticatedUser, str, int] | None:
        async with db_manager.session_factory() as session:
            return await auth_service.rotate_refresh_token(
                session=session,
                refresh_token=refresh_token,
                expires_minutes=60,
            )

    results = await asyncio.gather(rotate_once(), rotate_once())
    successful = [result for result in results if result is not None]

    assert len(successful) == 1


async def test_ensure_admin_user_is_idempotent_under_concurrency() -> None:
    async def ensure_once() -> bool:
        async with db_manager.session_factory() as session:
            return await auth_service.ensure_admin_user(
                session=session,
                username="admin-concurrent",
                password="super-secret-password",
                scopes=["items:read", "items:write"],
            )

    results = await asyncio.gather(*(ensure_once() for _ in range(8)))
    assert sum(1 for created in results if created) == 1

    async with db_manager.session_factory() as session:
        count_result = await session.execute(
            select(func.count(User.id)).where(User.username == "admin-concurrent")
        )
        count = count_result.scalar_one()

    assert count == 1
