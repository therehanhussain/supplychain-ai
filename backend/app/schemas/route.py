"""Supply Chain Route & Graph Topology Schemas."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SupplyRelationship(BaseModel):
    supplier: str
    consumer: str
    material: str
    price: float
    inventory: float
    usage_ratio: float


class RouteTopologyResponse(BaseModel):
    source: str = Field(..., description="'neo4j_cluster' or 'offline_fallback_dataset'")
    data_mode: str = Field(default="DEGRADED", description="'LIVE', 'DEGRADED', or 'UNAVAILABLE'")
    status_message: Optional[str] = Field(default=None, description="Human-readable provenance and status note")
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    tier_statistics: List[Dict[str, Any]] = Field(default_factory=list)
