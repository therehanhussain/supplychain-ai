"""Agent Simulation Pydantic Schemas."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class SimulationDispatchRequest(BaseModel):
    name: Optional[str] = Field(default=None, json_schema_extra={"example": "Automotive Tier-1 Simulation"})
    num_days: int = Field(default=4, ge=1, le=365)
    num_firms: int = Field(default=16, ge=2, le=100)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class SimulationDispatchResponse(BaseModel):
    experiment_id: str
    task_id: str
    status: str = "queued"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    message: str = "Simulation dispatched to background worker"


class AgentProfileResponse(BaseModel):
    agent_id: int
    company_name: str
    tier_level: int
    intelligence_level: int
    current_funds: float
    total_inventory: float
