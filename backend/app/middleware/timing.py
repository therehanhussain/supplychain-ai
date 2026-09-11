"""Latency & Timing Middleware.

Measures HTTP request execution duration, attaches X-Process-Time header,
and emits structured access logs with latency metrics.
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.core.logging import logger


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware tracking request latency and emitting structured logs."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        response: Response = await call_next(request)
        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response.headers["X-Process-Time"] = f"{process_time_ms}ms"

        # Emit structured log record
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(
            f"{request.method} {request.url.path} HTTP/{request.scope.get('http_version', '1.1')} "
            f"-> {response.status_code} ({process_time_ms}ms)",
            extra={
                "request_id": request_id,
                "latency_ms": process_time_ms,
            },
        )
        return response
