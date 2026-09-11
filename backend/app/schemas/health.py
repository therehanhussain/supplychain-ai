"""Health & Readiness Pydantic Schemas."""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """Basic service health status."""
    status: str = Field(..., description="'healthy' or 'degraded'")
    app: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Runtime environment")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ComponentHealth(BaseModel):
    """Individual dependency health status."""
    status: str = Field(..., description="'healthy', 'unreachable', or 'disabled'")
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class ReadyStatus(BaseModel):
    """Readiness probe status across dependencies."""
    status: str = Field(..., description="'ready' or 'not_ready'")
    dependencies: Dict[str, ComponentHealth] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LiveStatus(BaseModel):
    """Liveness probe status for process watchdog."""
    status: str = Field(default="alive")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
