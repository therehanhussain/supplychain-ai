"""Risk Assessment Pydantic Schemas."""

from typing import List, Dict, Any
from pydantic import BaseModel, Field


class DisruptionAnalysisRequest(BaseModel):
    supplier_id: str = Field(..., json_schema_extra={"example": "sup_001"})
    disruption_duration_days: int = Field(default=14, ge=1)


class DisruptionAnalysisResponse(BaseModel):
    supplier_id: str
    risk_level: str = Field(..., description="'low', 'medium', 'high', 'critical'")
    bottleneck_score: float = Field(..., ge=0.0, le=1.0)
    estimated_revenue_at_risk: float
    affected_downstream_products: List[str]
    mitigation_recommendations: List[str]
