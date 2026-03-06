from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from __PROJECT_SLUG__.core.config import Settings, get_settings


class DatabaseManager:
    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._configured_url: str | None = None

    def configure(self, settings: Settings) -> None:
        if self._engine is not None and self._configured_url == settings.database_url:
            return
        if self._engine is not None and self._configured_url != settings.database_url:
            # Reconfigure within the same process (common in tests/fixtures): dispose previous pool first.
            self._engine.sync_engine.dispose()
            self._engine = None
            self._session_factory = None
            self._configured_url = None

        engine_kwargs = {
            "echo": settings.database_echo,
            "pool_pre_ping": True,
        }

        if not settings.database_url.startswith("sqlite+"):
            engine_kwargs.update(
                {
                    "pool_size": settings.database_pool_size,
                    "max_overflow": settings.database_max_overflow,
                    "pool_timeout": settings.database_pool_timeout,
                    "pool_recycle": settings.database_pool_recycle,
                }
            )

        self._engine = create_async_engine(settings.database_url, **engine_kwargs)
        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        self._configured_url = settings.database_url

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self.configure(get_settings())
        assert self._session_factory is not None
        return self._session_factory

    async def ping(self) -> None:
        if self._engine is None:
            self.configure(get_settings())
        assert self._engine is not None
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def create_schema(self) -> None:
        if self._engine is None:
            self.configure(get_settings())
        assert self._engine is not None
        from __PROJECT_SLUG__.core.db.models import Base

        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
        self._engine = None
        self._session_factory = None
        self._configured_url = None


db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with db_manager.session_factory() as session:
        yield session
