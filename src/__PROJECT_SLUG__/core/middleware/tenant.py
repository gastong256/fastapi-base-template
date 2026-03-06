from contextvars import ContextVar

import structlog.contextvars
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

TENANT_HEADER = "X-Tenant-ID"
DEFAULT_TENANT = "public"

# Module-level ContextVar — safe for concurrent async requests because each
# coroutine inherits its own copy. The reset(token) in finally prevents leakage.
_tenant_id: ContextVar[str] = ContextVar("tenant_id", default=DEFAULT_TENANT)


def get_tenant_id() -> str:
    """Return the tenant ID for the current request context.

    Callable from route handlers via FastAPI Depends or directly from service code.
    """
    return _tenant_id.get()


async def get_tenant_id_dependency() -> str:
    """Async dependency wrapper to avoid threadpool execution for sync callables."""
    return get_tenant_id()


class TenantMiddleware:
    """Resolve X-Tenant-ID request header and store it in contextvars.

    Falls back to DEFAULT_TENANT ("public") when the header is absent.
    The tenant ID is also bound to structlog contextvars so it appears in
    every log record emitted during the request lifecycle.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        tenant_id = Headers(scope=scope).get(TENANT_HEADER, DEFAULT_TENANT)
        token = _tenant_id.set(tenant_id)
        structlog.contextvars.bind_contextvars(tenant_id=tenant_id)
        try:
            await self.app(scope, receive, send)
        finally:
            structlog.contextvars.unbind_contextvars("tenant_id")
            _tenant_id.reset(token)
