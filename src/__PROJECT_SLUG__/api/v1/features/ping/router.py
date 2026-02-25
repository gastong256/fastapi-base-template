from fastapi import APIRouter

from __PROJECT_SLUG__.api.v1.features.ping.schemas import PingResponse

router = APIRouter(prefix="/ping", tags=["ping"])


@router.get("", response_model=PingResponse)
async def ping() -> PingResponse:
    return PingResponse()
