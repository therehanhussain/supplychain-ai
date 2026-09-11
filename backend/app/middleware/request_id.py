"""Request ID Middleware.

Ensures every incoming HTTP request receives a unique UUID correlation identifier,
propagating it via the X-Request-ID header and request.state.
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware attaching a correlation request ID to every request/response cycle."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Honor client-provided X-Request-ID or generate new UUID v4
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
