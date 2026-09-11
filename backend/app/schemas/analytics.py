"""Analytics & KPI Pydantic Schemas."""

from typing import Dict, Any, List
from pydantic import BaseModel, Field


class AnalyticsSummaryResponse(BaseModel):
    total_suppliers: int = Field(default=16)
    active_orders: int = Field(default=42)
    total_inventory_value: float = Field(default=1542000.0)
    inventory_turnover_ratio: float = Field(default=4.8)
    on_time_delivery_rate: float = Field(default=0.94)
    critical_disruptions: int = Field(default=0)
    tier_distribution: Dict[str, int] = Field(default_factory=dict)
