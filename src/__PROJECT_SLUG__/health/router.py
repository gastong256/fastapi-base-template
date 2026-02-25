from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


health_router = APIRouter(tags=["Health"])


@health_router.get("/health", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """Liveness probe — confirms the process is running.

    Must never depend on external services. If this endpoint fails,
    the orchestrator will restart the container.
    """
    return HealthResponse(status="ok")


@health_router.get("/ready", response_model=HealthResponse)
async def readiness() -> HealthResponse:
    """Readiness probe — confirms the service is ready to accept traffic.

    Extend this endpoint to check downstream dependencies:
        - Database connectivity
        - Cache availability
        - Message broker reachability

    If any dependency is unavailable, raise HTTPException(503).
    """
    return HealthResponse(status="ok")
