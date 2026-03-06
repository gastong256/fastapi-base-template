from __future__ import annotations

import pytest_asyncio
from sqlalchemy import delete

from __PROJECT_SLUG__.api.v1.features.items.models import Item
from __PROJECT_SLUG__.core.config import get_settings
from __PROJECT_SLUG__.core.db import db_manager


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_db() -> None:
    db_manager.configure(get_settings())
    await db_manager.create_schema()
    yield
    await db_manager.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_items_table(prepare_db: None) -> None:
    async with db_manager.session_factory() as session:
        await session.execute(delete(Item))
        await session.commit()
    yield
    async with db_manager.session_factory() as session:
        await session.execute(delete(Item))
        await session.commit()
