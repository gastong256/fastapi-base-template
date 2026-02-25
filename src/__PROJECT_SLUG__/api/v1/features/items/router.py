from typing import Annotated

from fastapi import APIRouter, Depends, status

from __PROJECT_SLUG__.api.v1.features.items import service
from __PROJECT_SLUG__.api.v1.features.items.schemas import ItemCreate, ItemResponse
from __PROJECT_SLUG__.core.middleware.tenant import get_tenant_id

router = APIRouter(prefix="/items", tags=["items"])


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: ItemCreate,
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> ItemResponse:
    return service.create_item(payload, tenant_id)
