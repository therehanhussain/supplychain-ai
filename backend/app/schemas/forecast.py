"""Demand Forecast Pydantic Schemas."""

from typing import List
from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    product_id: str = Field(..., json_schema_extra={"example": "prod_101"})
    horizon_days: int = Field(default=30, ge=1, le=365)


class ForecastResponse(BaseModel):
    product_id: str
    horizon_days: int
    forecast_series: List[float]
    confidence_interval: float = 0.95
    trend: str = "stable"
    status: str = "completed"
