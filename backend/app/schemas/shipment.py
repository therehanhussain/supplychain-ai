"""Shipment Entity Pydantic Schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ShipmentBase(BaseModel):
    order_id: str = Field(..., json_schema_extra={"example": "ord_001"})
    carrier: str = Field(..., json_schema_extra={"example": "DHL Express"})
    tracking_number: Optional[str] = Field(default=None, json_schema_extra={"example": "DHL-984712093"})
    origin: str = Field(..., json_schema_extra={"example": "Warehouse A, Shanghai"})
    destination: str = Field(..., json_schema_extra={"example": "Distribution Center, Munich"})
    status: str = Field(default="in_transit", description="'preparing', 'in_transit', 'out_for_delivery', 'delivered'")
    estimated_delivery: Optional[datetime] = None


class ShipmentCreate(ShipmentBase):
    pass


class ShipmentResponse(ShipmentBase):
    id: str = Field(..., json_schema_extra={"example": "shp_001"})
    created_at: datetime = Field(default_factory=datetime.utcnow)
