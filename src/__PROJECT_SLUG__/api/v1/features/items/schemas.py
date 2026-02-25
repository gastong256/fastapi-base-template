from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["Widget"])
    description: str | None = Field(
        default=None,
        max_length=1000,
        examples=["A reusable widget component"],
    )
    price: float = Field(..., gt=0, examples=[9.99])

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Widget",
                "description": "A reusable widget component",
                "price": 9.99,
            }
        }
    }


class ItemResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    price: float
    tenant_id: str
    created_at: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Widget",
                "description": "A reusable widget component",
                "price": 9.99,
                "tenant_id": "acme",
                "created_at": "2024-01-01T00:00:00Z",
            }
        }
    }
