"""Inventory Entity Pydantic Schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class InventoryItemBase(BaseModel):
    sku: str = Field(..., json_schema_extra={"example": "MAT-RAW-001"})
    name: str = Field(..., json_schema_extra={"example": "High-Grade Silicon Wafer"})
    category: str = Field(default="raw_material", description="'raw_material', 'intermediate', 'finished_good'")
    quantity_on_hand: float = Field(default=0.0, ge=0.0)
    quantity_reserved: float = Field(default=0.0, ge=0.0)
    reorder_point: float = Field(default=100.0, ge=0.0)
    unit_cost: float = Field(default=25.50, ge=0.0)
    warehouse_id: str = Field(default="WH-01")


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemResponse(InventoryItemBase):
    id: str = Field(..., json_schema_extra={"example": "inv_001"})
    is_low_stock: bool = False
    updated_at: datetime = Field(default_factory=datetime.utcnow)
