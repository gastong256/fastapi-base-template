"""Items service — business logic layer.

Primary path persists to the configured database via SQLAlchemy repository.
An in-memory fallback remains for lightweight unit tests that bypass DI.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from __PROJECT_SLUG__.api.v1.features.items import repository
from __PROJECT_SLUG__.api.v1.features.items.schemas import ItemCreate, ItemResponse

# Replace with a proper repository / database session in production.
_store: dict[UUID, ItemResponse] = {}


def clear_store() -> None:
    _store.clear()


async def create_item(
    payload: ItemCreate,
    tenant_id: str,
    session: AsyncSession | None = None,
) -> ItemResponse:
    if session is None:
        return _create_item_in_memory(payload, tenant_id)

    repo = repository.ItemRepository(session)
    item = await repo.create(payload, tenant_id)

    return ItemResponse(
        id=item.id,
        name=item.name,
        description=item.description,
        price=float(item.price),
        tenant_id=item.tenant_id,
        created_at=item.created_at,
    )


def _create_item_in_memory(payload: ItemCreate, tenant_id: str) -> ItemResponse:
    item = ItemResponse(
        id=uuid.uuid4(),
        name=payload.name,
        description=payload.description,
        price=payload.price,
        tenant_id=tenant_id,
        created_at=datetime.now(UTC),
    )
    _store[item.id] = item
    return item
