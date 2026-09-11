"""Order Entity Pydantic Schemas."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class OrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)


class OrderBase(BaseModel):
    customer_name: str = Field(..., json_schema_extra={"example": "Global Tech Enterprises"})
    supplier_id: str = Field(..., json_schema_extra={"example": "sup_001"})
    items: List[OrderItem] = Field(default_factory=list)
    total_amount: float = Field(default=0.0, ge=0.0)
    status: str = Field(default="pending", description="'pending', 'confirmed', 'shipped', 'delivered', 'cancelled'")


class OrderCreate(OrderBase):
    pass


class OrderResponse(OrderBase):
    id: str = Field(..., json_schema_extra={"example": "ord_001"})
    created_at: datetime = Field(default_factory=datetime.utcnow)
