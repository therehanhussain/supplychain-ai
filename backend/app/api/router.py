"""Master API Router.

Assembles both the versioned /api/v1/* domain routes and the
backward-compatible /api/* legacy routes.
"""

from fastapi import APIRouter

from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.suppliers import router as suppliers_router
from backend.app.api.v1.inventory import router as inventory_router
from backend.app.api.v1.orders import router as orders_router
from backend.app.api.v1.shipments import router as shipments_router
from backend.app.api.v1.routes import router as routes_router
from backend.app.api.v1.forecast import router as forecast_router
from backend.app.api.v1.risk import router as risk_router
from backend.app.api.v1.agents import router as agents_router
from backend.app.api.v1.analytics import router as analytics_router
from backend.app.api.v1.manufacturing import router as manufacturing_router
from backend.app.api.legacy import router as legacy_router

# Master v1 router prefixing /api/v1
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health_router)
v1_router.include_router(auth_router)
v1_router.include_router(suppliers_router)
v1_router.include_router(inventory_router)
v1_router.include_router(orders_router)
v1_router.include_router(shipments_router)
v1_router.include_router(routes_router)
v1_router.include_router(forecast_router)
v1_router.include_router(risk_router)
v1_router.include_router(agents_router)
v1_router.include_router(analytics_router)
v1_router.include_router(manufacturing_router)


# Master root router
api_router = APIRouter()
api_router.include_router(v1_router)
api_router.include_router(legacy_router)
