"""Analytics & Telemetry API Endpoints (/api/v1/analytics)."""

from fastapi import APIRouter
from backend.app.schemas.analytics import AnalyticsSummaryResponse
from backend.app.core.config import settings

router = APIRouter(prefix="/analytics", tags=["Analytics & KPIs"])


@router.get("/summary", response_model=AnalyticsSummaryResponse, summary="Get global supply chain KPI summary")
async def get_analytics_summary():
    """Retrieve aggregate network metrics, delivery performance, and capital allocation."""
    return AnalyticsSummaryResponse(
        total_suppliers=16,
        active_orders=38,
        total_inventory_value=1845000.0,
        inventory_turnover_ratio=5.2,
        on_time_delivery_rate=0.96,
        critical_disruptions=0,
        tier_distribution={"tier_1": 4, "tier_2": 6, "tier_3": 6},
    )


@router.get("/telemetry-url", summary="Get MLflow telemetry dashboard link")
async def get_telemetry_url():
    """Returns safe external tracking URL for MLflow metrics without credentials."""
    return {
        "service": "mlflow",
        "tracking_uri": settings.MLFLOW_TRACKING_URI,
    }
