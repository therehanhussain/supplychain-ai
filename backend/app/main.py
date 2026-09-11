"""SupplyChainAgent Production Backend Entrypoint.

This module serves as the primary ASGI application for the production SaaS platform.
During the Phase 2 migration stage, it establishes the target clean architecture
and provides an adapter layer for existing legacy routes and data access.
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

# Ensure repository root is in Python path for transitional module access
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    # Startup: initialize connections and service registries
    yield
    # Shutdown: cleanly close open connection pools


def create_application() -> FastAPI:
    """Application factory for the production FastAPI service."""
    app = FastAPI(
        title="SupplyChainAgent SaaS API",
        version="0.1.0",
        description="Production API for AI-powered multi-agent supply chain simulation and intelligence.",
        lifespan=lifespan,
    )

    # Base CORS setup (will be parameterized via Settings in Phase 4/6)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["System Probes"])
    async def health_check() -> Dict[str, Any]:
        """Liveness health probe."""
        return {
            "status": "healthy",
            "phase": "Phase 2 - Architecture & Migration Scaffold",
            "version": "0.1.0"
        }

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
