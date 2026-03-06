from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from __PROJECT_SLUG__.api.v1.router import v1_router
from __PROJECT_SLUG__.api.v1.features.auth.service import seed_admin_user_if_enabled
from __PROJECT_SLUG__.core.config import get_settings
from __PROJECT_SLUG__.core.db import db_manager
from __PROJECT_SLUG__.core.errors import register_exception_handlers
from __PROJECT_SLUG__.core.logging import configure_logging
from __PROJECT_SLUG__.core.metrics import MetricsMiddleware, metrics_endpoint
from __PROJECT_SLUG__.core.middleware.body_size import RequestBodyLimitMiddleware
from __PROJECT_SLUG__.core.middleware.rate_limit import (
    RateLimitMiddleware,
    build_rate_limiter,
)
from __PROJECT_SLUG__.core.middleware.request_id import RequestIDMiddleware
from __PROJECT_SLUG__.core.middleware.security_headers import SecurityHeadersMiddleware
from __PROJECT_SLUG__.core.middleware.tenant import TenantMiddleware
from __PROJECT_SLUG__.core.middleware.timeout import RequestTimeoutMiddleware
from __PROJECT_SLUG__.core.readiness import (
    STARTUP_COMPLETE_STATE_KEY,
    configure_readiness,
    register_readiness_check,
)
from __PROJECT_SLUG__.health.router import health_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(debug=settings.debug, level=settings.log_level)
    db_manager.configure(settings)
    rate_limit_exempt_paths = set(settings.rate_limit_exempt_paths)
    request_timeout_exempt_paths = set(settings.request_timeout_exempt_paths)
    request_body_limit_exempt_paths = set(settings.request_body_limit_exempt_paths)
    if settings.metrics_enabled:
        rate_limit_exempt_paths.add(settings.metrics_path)
        request_timeout_exempt_paths.add(settings.metrics_path)
        request_body_limit_exempt_paths.add(settings.metrics_path)

    limiter = (
        build_rate_limiter(
            backend=settings.rate_limit_backend,
            max_requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
            memory_max_keys=settings.rate_limit_memory_max_keys,
            redis_url=settings.rate_limit_redis_url,
            redis_prefix=settings.rate_limit_redis_prefix,
        )
        if settings.rate_limit_enabled
        else None
    )

    async def database_readiness_check(_app: FastAPI) -> None:
        await db_manager.ping()

    async def rate_limit_backend_readiness_check(_app: FastAPI) -> None:
        if limiter is not None:
            await limiter.ping()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        setattr(app.state, STARTUP_COMPLETE_STATE_KEY, False)
        if settings.database_auto_create_schema:
            await db_manager.create_schema()
        if settings.database_connect_on_startup:
            await db_manager.ping()
        if settings.auth_use_database:
            await seed_admin_user_if_enabled(
                enabled=settings.auth_seed_admin_on_startup,
                session_factory=db_manager.session_factory,
                username=settings.auth_admin_username,
                password=settings.auth_admin_password,
                scopes=settings.auth_admin_scopes,
            )
        if settings.otel_enabled:
            from __PROJECT_SLUG__.core.otel import setup_otel

            setup_otel(app, settings.otel_service_name, settings.otel_endpoint)
        setattr(app.state, STARTUP_COMPLETE_STATE_KEY, True)
        try:
            yield
        finally:
            setattr(app.state, STARTUP_COMPLETE_STATE_KEY, False)
            if limiter is not None:
                await limiter.close()
            await db_manager.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description=settings.description,
        docs_url=settings.api_docs_url if settings.api_docs_enabled else None,
        redoc_url=settings.api_redoc_url if settings.api_docs_enabled else None,
        openapi_url=settings.api_openapi_url if settings.api_docs_enabled else None,
        lifespan=lifespan,
    )

    register_exception_handlers(app)

    if settings.metrics_enabled:
        app.add_api_route(
            settings.metrics_path,
            metrics_endpoint,
            methods=["GET"],
            include_in_schema=False,
        )

    configure_readiness(app)
    register_readiness_check(app, "database", database_readiness_check)
    if settings.rate_limit_enabled and settings.rate_limit_backend == "redis":
        register_readiness_check(app, "rate_limit_backend", rate_limit_backend_readiness_check)

    if settings.cors_origins:
        allow_origins = [
            f"{origin.scheme}://{origin.host}{f':{origin.port}' if origin.port else ''}"
            for origin in settings.cors_origins
        ]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    if settings.allowed_hosts and settings.allowed_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    if settings.gzip_enabled:
        app.add_middleware(
            GZipMiddleware,
            minimum_size=settings.gzip_minimum_size,
            compresslevel=settings.gzip_compress_level,
        )

    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            limiter=limiter,
            exempt_paths=rate_limit_exempt_paths,
            fail_open=settings.rate_limit_fail_open,
            trust_x_forwarded_for=settings.trust_x_forwarded_for,
        )

    if settings.request_timeout_enabled:
        app.add_middleware(
            RequestTimeoutMiddleware,
            timeout_seconds=settings.request_timeout_seconds,
            exempt_paths=request_timeout_exempt_paths,
        )

    if settings.request_body_limit_enabled:
        app.add_middleware(
            RequestBodyLimitMiddleware,
            max_body_bytes=settings.request_body_max_bytes,
            exempt_paths=request_body_limit_exempt_paths,
        )

    if settings.security_headers_enabled:
        app.add_middleware(
            SecurityHeadersMiddleware,
            csp=settings.security_csp,
            hsts_enabled=settings.security_hsts_enabled,
            hsts_seconds=settings.security_hsts_seconds,
        )

    if settings.metrics_enabled:
        app.add_middleware(
            MetricsMiddleware,
            metrics_path=settings.metrics_path,
        )

    # Starlette executes middleware in reverse registration order (last added first).
    # RequestID must run first to bind request_id for every downstream middleware log.
    # SecurityHeaders wraps all downstream responses, including early 429 rate-limit responses.
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RequestIDMiddleware)

    app.include_router(health_router)  # /health  /ready  (root, no versioning)
    app.include_router(v1_router, prefix="/api/v1")  # /api/v1/...

    return app


app = create_app()
