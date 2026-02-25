from contextlib import asynccontextmanager

from fastapi import FastAPI

from __PROJECT_SLUG__.api.v1.router import v1_router
from __PROJECT_SLUG__.core.config import get_settings
from __PROJECT_SLUG__.core.errors import register_exception_handlers
from __PROJECT_SLUG__.core.logging import configure_logging
from __PROJECT_SLUG__.core.middleware.request_id import RequestIDMiddleware
from __PROJECT_SLUG__.core.middleware.tenant import TenantMiddleware
from __PROJECT_SLUG__.health.router import health_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(debug=settings.debug)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.otel_enabled:
            from __PROJECT_SLUG__.core.otel import setup_otel

            setup_otel(settings.otel_service_name, settings.otel_endpoint)
        yield

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description=settings.description,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    register_exception_handlers(app)

    # Starlette middleware is a LIFO stack.
    # RequestIDMiddleware is added first so it executes first on every request,
    # ensuring request_id is bound to structlog context before TenantMiddleware runs.
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(TenantMiddleware)

    app.include_router(health_router)  # /health  /ready  (root, no versioning)
    app.include_router(v1_router, prefix="/api/v1")  # /api/v1/...

    return app


app = create_app()
