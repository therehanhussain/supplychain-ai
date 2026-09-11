"""Supplier Entity Pydantic Schemas."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class SupplierBase(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Apex Raw Materials Co."})
    tier: int = Field(default=1, ge=1, le=4, description="Supply chain tier: 1=Primary, 2=Intermediate, etc.")
    contact_email: Optional[str] = Field(default=None, json_schema_extra={"example": "contact@apexmaterials.com"})
    location: Optional[str] = Field(default=None, json_schema_extra={"example": "Shanghai, CN"})
    country: Optional[str] = Field(default="Global", json_schema_extra={"example": "China"})
    reliability_score: float = Field(default=0.95, ge=0.0, le=1.0)
    rating: Optional[float] = Field(default=5.0, ge=0.0, le=5.0)


    lead_time_days: int = Field(default=7, ge=1)
    status: str = Field(default="active", description="'active', 'suspended', 'under_review'")


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    tier: Optional[int] = Field(default=None, ge=1, le=4)
    contact_email: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    reliability_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    lead_time_days: Optional[int] = Field(default=None, ge=1)
    status: Optional[str] = None


class SupplierResponse(SupplierBase):
    id: str = Field(..., json_schema_extra={"example": "sup_001"})
    created_at: datetime = Field(default_factory=datetime.utcnow)
    materials_supplied: List[str] = Field(default_factory=list)

