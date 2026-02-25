from fastapi import APIRouter

from __PROJECT_SLUG__.api.v1.features.items.router import router as items_router
from __PROJECT_SLUG__.api.v1.features.ping.router import router as ping_router

v1_router = APIRouter()
v1_router.include_router(ping_router)
v1_router.include_router(items_router)
