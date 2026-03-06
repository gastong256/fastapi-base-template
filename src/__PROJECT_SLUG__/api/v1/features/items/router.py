from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from __PROJECT_SLUG__.api.v1.features.items import service
from __PROJECT_SLUG__.api.v1.features.items.schemas import ItemCreate, ItemResponse
from __PROJECT_SLUG__.core.db import get_db_session
from __PROJECT_SLUG__.core.middleware.tenant import get_tenant_id

router = APIRouter(prefix="/items", tags=["items"])


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: ItemCreate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ItemResponse:
    return await service.create_item(payload, tenant_id, db_session)
