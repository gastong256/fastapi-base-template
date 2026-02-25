from contextvars import ContextVar

import structlog.contextvars
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

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


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve X-Tenant-ID request header and store it in contextvars.

    Falls back to DEFAULT_TENANT ("public") when the header is absent.
    The tenant ID is also bound to structlog contextvars so it appears in
    every log record emitted during the request lifecycle.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        tenant_id = request.headers.get(TENANT_HEADER, DEFAULT_TENANT)
        token = _tenant_id.set(tenant_id)
        structlog.contextvars.bind_contextvars(tenant_id=tenant_id)
        try:
            return await call_next(request)
        finally:
            _tenant_id.reset(token)
