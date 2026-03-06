from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from __PROJECT_SLUG__.core.readiness import run_readiness_checks


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
async def readiness(request: Request) -> HealthResponse:
    """Readiness probe — confirms the service is ready to accept traffic.

    Returns 503 if any configured readiness check fails.
    """
    failed_checks = await run_readiness_checks(request.app)
    if failed_checks:
        checks = ", ".join(failed_checks)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Readiness checks failed: {checks}",
        )

    return HealthResponse(status="ok")
