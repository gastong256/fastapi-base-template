import uuid

import structlog
import structlog.contextvars
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Generate or propagate X-Request-ID, bind it to the structlog context.

    If the incoming request already carries X-Request-ID (e.g. from an upstream
    gateway), that value is preserved and echoed back in the response header.
    Otherwise a new UUID4 is generated.

    structlog.contextvars is cleared at the start of every request to prevent
    context leakage between concurrent requests sharing the same worker process.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
