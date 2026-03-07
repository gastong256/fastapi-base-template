from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from __PROJECT_SLUG__.api.v1.features.auth.models import RefreshToken, User


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_by_username(self, username: str) -> User | None:
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create_user(
        self,
        *,
        username: str,
        password_hash: str,
        scopes_csv: str,
        is_active: bool,
        commit: bool = True,
    ) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            scopes_csv=scopes_csv,
            is_active=is_active,
        )
        self.session.add(user)
        await self.session.flush()
        if commit:
            await self.session.commit()
            await self.session.refresh(user)
        return user

    async def create_refresh_token(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        commit: bool = True,
    ) -> RefreshToken:
        refresh = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(refresh)
        await self.session.flush()
        if commit:
            await self.session.commit()
            await self.session.refresh(refresh)
        return refresh

    async def get_valid_refresh_token(self, token_hash: str) -> RefreshToken | None:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def consume_refresh_token(self, token_hash: str, *, commit: bool = True) -> UUID | None:
        now = datetime.now(UTC)
        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .values(revoked_at=now)
            .returning(RefreshToken.user_id)
        )
        result = await self.session.execute(statement)
        user_id = result.scalar_one_or_none()
        if user_id is not None and commit:
            await self.session.commit()
        return user_id

    async def revoke_refresh_token(self, token_hash: str, *, commit: bool = True) -> bool:
        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
            .returning(RefreshToken.id)
        )
        result = await self.session.execute(statement)
        changed = result.scalar_one_or_none() is not None
        if changed and commit:
            await self.session.commit()
        return changed
