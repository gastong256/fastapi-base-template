from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from __PROJECT_SLUG__.api.v1.features.items.models import Item
from __PROJECT_SLUG__.api.v1.features.items.schemas import ItemCreate


class ItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, payload: ItemCreate, tenant_id: str) -> Item:
        item = Item(
            name=payload.name,
            description=payload.description,
            price=Decimal(str(payload.price)),
            tenant_id=tenant_id,
        )
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item
