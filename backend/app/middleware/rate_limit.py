"""Rate Limiting Middleware.

Enforces tiered request rate limits per client IP / authenticated subject to protect
against denial of service, resource exhaustion, and simulation over-dispatch.
"""

import time
import asyncio
from collections import defaultdict
from typing import Dict, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from backend.app.core.config import settings


class InMemoryRateLimiter:
    """Sliding-window request rate limiter."""

    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str, max_requests: int) -> Tuple[bool, int]:
        """Check if request is allowed under the rate limit.
        
        Returns:
            (allowed: bool, retry_after: int)
        """
        now = time.time()
        window_start = now - self.window_seconds

        async with self._lock:
            # Purge timestamps outside the current window
            timestamps = [t for t in self._requests[key] if t > window_start]
            if len(timestamps) >= max_requests:
                earliest = timestamps[0]
                retry_after = max(1, int(self.window_seconds - (now - earliest)))
                self._requests[key] = timestamps
                return False, retry_after

            timestamps.append(now)
            self._requests[key] = timestamps
            return True, 0

    async def reset(self):
        """Clear all rate limit state (useful in test suites)."""
        async with self._lock:
            self._requests.clear()


limiter = InMemoryRateLimiter(window_seconds=60)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Tiered rate limiting middleware for FastAPI."""

    # Paths exempt from rate limiting
    EXEMPT_PATHS = {
        "/health",
        "/live",
        "/ready",
        "/api/v1/health",
        "/api/v1/live",
        "/api/v1/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/docs/oauth2-redirect",
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        path = request.url.path
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        # 1. Determine client identifier (authenticated token or client IP)
        auth_header = request.headers.get("Authorization", "")
        client_ip = request.client.host if request.client else "unknown_ip"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        is_authenticated = bool(auth_header.startswith("Bearer ") and len(auth_header) > 15)

        # 2. Determine rate limit tier based on path and auth
        if "/simulations" in path or "/run-experiments" in path or "/analyze-disruption" in path:
            max_requests = settings.RATE_LIMIT_SIMULATION
            key = f"sim:{client_ip}:{auth_header[-16:] if is_authenticated else ''}"
        elif is_authenticated:
            max_requests = settings.RATE_LIMIT_AUTHENTICATED
            key = f"auth:{auth_header[-16:]}"
        else:
            max_requests = settings.RATE_LIMIT_UNAUTHENTICATED
            key = f"unauth:{client_ip}"

        # 3. Check rate limit
        allowed, retry_after = await limiter.is_allowed(key, max_requests)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "detail": "Rate limit exceeded. Please slow down your requests.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
