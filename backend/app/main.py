"""SupplyChainAgent Production Backend Application.

Primary ASGI entrypoint integrating production versioned APIs (/api/v1/*),
legacy compatibility routes (/api/*), request correlation, structured JSON logging,
custom error handling, and container orchestration probes.
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

# Ensure repository root is in Python sys.path for transitional imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.exceptions import register_exception_handlers
from backend.app.middleware.request_id import RequestIdMiddleware
from backend.app.middleware.timing import TimingMiddleware
from backend.app.middleware.security_headers import SecurityHeadersMiddleware
from backend.app.middleware.rate_limit import RateLimitMiddleware
from backend.app.api.router import api_router
from backend.app.api.v1.health import router as root_health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [Environment: {settings.ENVIRONMENT}]",
        extra={"environment": settings.ENVIRONMENT},
    )
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_application() -> FastAPI:
    """Application factory configuring middleware, exception handlers, and routing."""
    app = FastAPI(
        title="SupplyChainAgent Production API",
        version=settings.APP_VERSION,
        description="Production SaaS API for AI-powered multi-agent supply chain intelligence.",
        lifespan=lifespan,
    )

    # 1. Request ID correlation middleware (outermost to tag all responses)
    app.add_middleware(RequestIdMiddleware)

    # 2. Timing and access latency logging middleware
    app.add_middleware(TimingMiddleware)

    # 3. OWASP Security Headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # 4. Tiered Rate Limiting middleware
    app.add_middleware(RateLimitMiddleware)

    # 5. Explicit CORS configuration (strictly from settings, no wildcard with credentials)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    # 4. Register custom uniform error handlers
    register_exception_handlers(app)

    # 5. Root orchestration probes (/health, /live, /ready)
    app.include_router(root_health_router)

    # 6. Master API routes (/api/v1/* and legacy /api/*)
    app.include_router(api_router)

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
