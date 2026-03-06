from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from __PROJECT_SLUG__.api.v1.features.items.models import Item
from __PROJECT_SLUG__.api.v1.features.items.repository import ItemRepository
from __PROJECT_SLUG__.api.v1.features.items.schemas import ItemCreate
from __PROJECT_SLUG__.api.v1.features.items.service import create_item
from __PROJECT_SLUG__.core.db import db_manager


async def test_item_repository_persists_item() -> None:
    async with db_manager.session_factory() as session:
        repo = ItemRepository(session)
        created = await repo.create(
            ItemCreate(name="Persistent Widget", description="Stored in db", price=4.25),
            tenant_id="acme",
        )

    async with db_manager.session_factory() as session:
        result = await session.execute(select(Item).where(Item.id == created.id))
        item = result.scalar_one()

    assert item.name == "Persistent Widget"
    assert item.description == "Stored in db"
    assert item.price == Decimal("4.25")
    assert item.tenant_id == "acme"


async def test_create_item_service_uses_database_session_when_provided() -> None:
    async with db_manager.session_factory() as session:
        response = await create_item(
            ItemCreate(name="Service Widget", price=9.99),
            tenant_id="tenant-x",
            session=session,
        )

    async with db_manager.session_factory() as session:
        result = await session.execute(select(Item).where(Item.id == response.id))
        persisted = result.scalar_one()

    assert response.tenant_id == "tenant-x"
    assert float(persisted.price) == 9.99
