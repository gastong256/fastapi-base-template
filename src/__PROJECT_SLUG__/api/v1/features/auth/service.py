from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
from hashlib import sha256
import os
import secrets
from uuid import UUID

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import InvalidHashError, VerifyMismatchError

    _ARGON2_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on installed runtime deps
    PasswordHasher = None  # type: ignore[assignment,misc]
    InvalidHashError = ValueError  # type: ignore[assignment,misc]
    VerifyMismatchError = ValueError  # type: ignore[assignment,misc]
    _ARGON2_AVAILABLE = False
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from __PROJECT_SLUG__.api.v1.features.auth.models import User
from __PROJECT_SLUG__.api.v1.features.auth.repository import AuthRepository

_password_hasher = PasswordHasher() if _ARGON2_AVAILABLE else None
_PBKDF2_SCHEME = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 390000


@dataclass(slots=True)
class AuthenticatedUser:
    user_id: UUID
    username: str
    scopes: list[str]


def _normalize_scopes(scopes: list[str]) -> list[str]:
    return sorted({scope.strip() for scope in scopes if scope.strip()})


def scopes_to_csv(scopes: list[str]) -> str:
    return ",".join(_normalize_scopes(scopes))


def scopes_from_csv(scopes_csv: str) -> list[str]:
    if not scopes_csv.strip():
        return []
    return _normalize_scopes(scopes_csv.split(","))


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8"))


def _hash_password_pbkdf2(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return f"{_PBKDF2_SCHEME}${_PBKDF2_ITERATIONS}${_b64encode(salt)}${_b64encode(derived)}"


def _verify_password_pbkdf2(password: str, password_hash: str) -> bool:
    parts = password_hash.split("$")
    if len(parts) != 4 or parts[0] != _PBKDF2_SCHEME:
        return False

    try:
        iterations = int(parts[1])
        salt = _b64decode(parts[2])
        expected = _b64decode(parts[3])
    except (TypeError, ValueError):
        return False

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(derived, expected)


def hash_password(password: str) -> str:
    if _password_hasher is not None:
        return _password_hasher.hash(password)
    return _hash_password_pbkdf2(password)


def verify_password(password: str, password_hash: str) -> bool:
    if password_hash.startswith(f"{_PBKDF2_SCHEME}$"):
        return _verify_password_pbkdf2(password, password_hash)
    if _password_hasher is None:
        return False

    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def hash_refresh_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


async def authenticate_database_user(
    *,
    username: str,
    password: str,
    session: AsyncSession,
) -> AuthenticatedUser | None:
    repo = AuthRepository(session)
    user = await repo.get_user_by_username(username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None

    return AuthenticatedUser(
        user_id=user.id,
        username=user.username,
        scopes=scopes_from_csv(user.scopes_csv),
    )


async def ensure_admin_user(
    *,
    session: AsyncSession,
    username: str,
    password: str,
    scopes: list[str],
) -> bool:
    repo = AuthRepository(session)
    existing = await repo.get_user_by_username(username)
    if existing is not None:
        return False

    await repo.create_user(
        username=username,
        password_hash=hash_password(password),
        scopes_csv=scopes_to_csv(scopes),
        is_active=True,
    )
    return True


async def seed_admin_user_if_enabled(
    *,
    enabled: bool,
    session_factory: async_sessionmaker[AsyncSession],
    username: str,
    password: str,
    scopes: list[str],
) -> bool:
    if not enabled:
        return False

    async with session_factory() as session:
        return await ensure_admin_user(
            session=session,
            username=username,
            password=password,
            scopes=scopes,
        )


async def issue_refresh_token(
    *,
    session: AsyncSession,
    user_id: UUID,
    expires_minutes: int,
) -> tuple[str, int]:
    repo = AuthRepository(session)
    raw_token = secrets.token_urlsafe(48)
    expires_delta = timedelta(minutes=expires_minutes)
    expires_at = datetime.now(UTC) + expires_delta

    await repo.create_refresh_token(
        user_id=user_id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=expires_at,
    )

    return raw_token, int(expires_delta.total_seconds())


async def rotate_refresh_token(
    *,
    session: AsyncSession,
    refresh_token: str,
    expires_minutes: int,
) -> tuple[AuthenticatedUser, str, int] | None:
    repo = AuthRepository(session)
    token_hash = hash_refresh_token(refresh_token)
    stored = await repo.get_valid_refresh_token(token_hash)
    if stored is None:
        return None

    user = await repo.get_user_by_id(stored.user_id)
    if user is None or not user.is_active:
        return None

    await repo.revoke_refresh_token(token_hash)

    new_refresh_token, refresh_expires_in = await issue_refresh_token(
        session=session,
        user_id=user.id,
        expires_minutes=expires_minutes,
    )
    principal = AuthenticatedUser(
        user_id=user.id,
        username=user.username,
        scopes=scopes_from_csv(user.scopes_csv),
    )
    return principal, new_refresh_token, refresh_expires_in


async def revoke_refresh_token(*, session: AsyncSession, refresh_token: str) -> bool:
    repo = AuthRepository(session)
    return await repo.revoke_refresh_token(hash_refresh_token(refresh_token))


def user_to_principal(user: User) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=user.id,
        username=user.username,
        scopes=scopes_from_csv(user.scopes_csv),
    )
