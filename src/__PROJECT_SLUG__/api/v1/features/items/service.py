"""Items service — business logic layer.

The in-memory store below is intentionally trivial. To add persistence:
1. Introduce a repository abstraction (e.g. items/repository.py).
2. Inject a database session via FastAPI Depends in the router.
3. Replace _store operations with repository calls.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

from __PROJECT_SLUG__.api.v1.features.items.schemas import ItemCreate, ItemResponse

# Replace with a proper repository / database session in production.
_store: dict[UUID, ItemResponse] = {}


def create_item(payload: ItemCreate, tenant_id: str) -> ItemResponse:
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
