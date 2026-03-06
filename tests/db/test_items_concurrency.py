from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from __PROJECT_SLUG__.api.v1.features.items.models import Item
from __PROJECT_SLUG__.api.v1.features.items.schemas import ItemCreate
from __PROJECT_SLUG__.api.v1.features.items.service import create_item
from __PROJECT_SLUG__.core.db import db_manager


async def test_concurrent_item_creates_are_persisted() -> None:
    async def create_one(i: int) -> str:
        async with db_manager.session_factory() as session:
            item = await create_item(
                ItemCreate(name=f"Item {i}", price=float(i + 1)),
                tenant_id=f"tenant-{i % 3}",
                session=session,
            )
            return str(item.id)

    ids = await asyncio.gather(*(create_one(i) for i in range(20)))

    assert len(ids) == 20
    assert len(set(ids)) == 20

    async with db_manager.session_factory() as session:
        count_result = await session.execute(select(func.count(Item.id)))
        total_items = count_result.scalar_one()

    assert total_items == 20
