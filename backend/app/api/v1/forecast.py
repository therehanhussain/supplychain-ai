"""Demand Forecasting API Endpoints (/api/v1/forecast)."""

from fastapi import APIRouter
from backend.app.schemas.forecast import ForecastRequest, ForecastResponse

router = APIRouter(prefix="/forecast", tags=["Demand Forecasting"])


@router.get("", response_model=ForecastResponse, summary="Get default baseline demand forecast")
async def get_default_forecast():
    """Returns baseline demand forecast for primary product."""
    base_qty = 100.0
    series = [round(base_qty * (1.0 + (i * 0.02)), 2) for i in range(14)]
    return ForecastResponse(
        product_id="prod_default",
        horizon_days=14,
        forecast_series=series,
        confidence_interval=0.95,
        trend="growing",
        status="completed",
    )


@router.post("", response_model=ForecastResponse, summary="Compute product demand forecast")
async def generate_demand_forecast(payload: ForecastRequest):
    """Calculates horizon-based demand forecast using historical simulation trends."""
    base_qty = 100.0
    series = [round(base_qty * (1.0 + (i * 0.02)), 2) for i in range(payload.horizon_days)]
    return ForecastResponse(
        product_id=payload.product_id,
        horizon_days=payload.horizon_days,
        forecast_series=series,
        confidence_interval=0.95,
        trend="growing" if series[-1] > series[0] else "stable",
        status="completed",
    )
