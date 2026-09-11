"""Production Security Headers Middleware.

Injects strict OWASP-recommended HTTP security headers on all API responses
to prevent MIME-sniffing, clickjacking, cross-site scripting, and credential leaks.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard security headers to every outgoing HTTP response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # 1. Prevent MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 2. Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # 3. Enable legacy browser XSS filters
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 4. Strict referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 5. Restrict device feature permissions
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

        # 6. HTTP Strict Transport Security (HSTS) in production
        if settings.ENVIRONMENT.lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return response
