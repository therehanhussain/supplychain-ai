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
    source: str = Field(..., description="'neo4j' or 'fallback_file'")
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    tier_statistics: List[Dict[str, Any]] = Field(default_factory=list)
