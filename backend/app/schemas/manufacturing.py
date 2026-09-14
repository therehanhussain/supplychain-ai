"""Pydantic schemas for manufacturing operations, work orders, and material transactions."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from backend.app.models.enums import (
    UnitOfMeasure,
    MaterialCategory,
    ProductionOrderStatus,
    WorkOrderStatus,
    TransactionType,
)


# ------------------------------------------------------------------------------
# Production Order Schemas
# ------------------------------------------------------------------------------

class ProductionOrderBase(BaseModel):
    order_number: str = Field(..., min_length=2, max_length=100, json_schema_extra={"example": "PO-2026-001"})
    product_id: str = Field(..., json_schema_extra={"example": "prod-finished-good-01"})
    planned_quantity: float = Field(..., gt=0.0, json_schema_extra={"example": 100.0})
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    notes: Optional[str] = None


class ProductionOrderCreate(ProductionOrderBase):
    pass


class ProductionOrderResponse(ProductionOrderBase):
    id: str
    organization_id: str
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    completed_quantity: float = 0.0
    status: ProductionOrderStatus
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------------------
# Work Order Schemas
# ------------------------------------------------------------------------------

class WorkOrderBase(BaseModel):
    production_order_id: str = Field(..., json_schema_extra={"example": "po-uuid-001"})
    work_order_number: str = Field(..., min_length=2, max_length=100, json_schema_extra={"example": "MO-1025"})
    warehouse_id: Optional[str] = None
    production_area: Optional[str] = Field(None, json_schema_extra={"example": "Winding Line 2"})
    assigned_user_id: Optional[str] = None
    planned_quantity: float = Field(..., gt=0.0, json_schema_extra={"example": 100.0})
    notes: Optional[str] = None


class WorkOrderCreate(WorkOrderBase):
    pass


class WorkOrderResponse(WorkOrderBase):
    id: str
    organization_id: str
    completed_quantity: float = 0.0
    status: WorkOrderStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------------------
# Material Requirement Schemas
# ------------------------------------------------------------------------------

class MaterialRequirementBase(BaseModel):
    production_order_id: Optional[str] = None
    work_order_id: Optional[str] = None
    product_id: str = Field(..., json_schema_extra={"example": "prod-raw-copper-wire"})
    required_quantity: float = Field(..., gt=0.0, json_schema_extra={"example": 50.0})
    unit_of_measure: str = Field(default=UnitOfMeasure.KG.value, json_schema_extra={"example": "kg"})


class MaterialRequirementCreate(MaterialRequirementBase):
    pass


class MaterialRequirementResponse(MaterialRequirementBase):
    id: str
    organization_id: str
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    issued_quantity: float = 0.0
    consumed_quantity: float = 0.0
    returned_quantity: float = 0.0
    wastage_quantity: float = 0.0
    remaining_issued_holding: float = 0.0
    variance_quantity: float = 0.0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------------------
# Stock Transaction Schemas
# ------------------------------------------------------------------------------

class StockTransactionCreate(BaseModel):
    inventory_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    product_id: Optional[str] = None
    transaction_type: TransactionType
    quantity: float = Field(..., gt=0.0, description="Movement quantity (strictly positive)")
    unit_of_measure: Optional[str] = "piece"
    work_order_id: Optional[str] = None
    production_order_id: Optional[str] = None
    employee_id: Optional[str] = None
    reason: Optional[str] = None
    source_location: Optional[str] = None
    destination_location: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def validate_positive_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Transaction quantity must be strictly greater than 0.")
        return round(v, 4)


class StockTransferCreate(BaseModel):
    source_warehouse_id: str = Field(..., json_schema_extra={"example": "wh-source-01"})
    destination_warehouse_id: str = Field(..., json_schema_extra={"example": "wh-dest-02"})
    product_id: str = Field(..., json_schema_extra={"example": "prod-copper-01"})
    quantity: float = Field(..., gt=0.0)
    unit_of_measure: Optional[str] = "kg"
    reason: Optional[str] = "Inter-facility replenishment"
    notes: Optional[str] = None


class StockTransactionResponse(BaseModel):
    id: str
    organization_id: str
    inventory_id: str
    product_id: str
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    warehouse_id: str
    warehouse_code: Optional[str] = None
    work_order_id: Optional[str] = None
    production_order_id: Optional[str] = None
    employee_id: Optional[str] = None
    employee_name: Optional[str] = None
    performed_by_user_id: str
    performed_by_name: Optional[str] = None
    transaction_type: TransactionType
    quantity: float
    unit_of_measure: str
    reason: Optional[str] = None
    source_location: Optional[str] = None
    destination_location: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------------------
# Material Traceability Timeline Schemas
# ------------------------------------------------------------------------------

class TraceabilityTimelineEntry(BaseModel):
    timestamp: datetime
    transaction_type: str
    quantity: float
    unit_of_measure: str
    who: str
    what_material: str
    where: str
    why: Optional[str] = None
    work_order: Optional[str] = None
    source_location: Optional[str] = None
    destination_location: Optional[str] = None
    reference: Optional[str] = None


class TraceabilityTimelineResponse(BaseModel):
    product_id: str
    sku: str
    name: str
    unit_of_measure: str
    current_stock_total: float
    timeline: List[TraceabilityTimelineEntry]


# ------------------------------------------------------------------------------
# Material Request Schemas (Phase 13.2)
# ------------------------------------------------------------------------------

class MaterialRequestCreate(BaseModel):
    work_order_id: str = Field(..., json_schema_extra={"example": "wo-uuid-001"})
    product_id: str = Field(..., json_schema_extra={"example": "prod-uuid-001"})
    quantity: float = Field(..., gt=0.0, description="Requested quantity (strictly positive)")
    unit_of_measure: Optional[str] = "kg"
    reason: str = Field(..., min_length=1, max_length=255, json_schema_extra={"example": "Line replenishment"})
    notes: Optional[str] = None


class MaterialRequestResponse(BaseModel):
    id: str
    organization_id: str
    work_order_id: str
    work_order_number: Optional[str] = None
    product_id: str
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    requested_by_user_id: str
    requested_by_name: Optional[str] = None
    quantity: float
    unit_of_measure: Optional[str] = None
    status: str
    reason: str
    notes: Optional[str] = None
    reviewed_by_user_id: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    rejection_reason: Optional[str] = None
    issued_transaction_id: Optional[str] = None
    warehouse_stock: Optional[float] = None
    holding_quantity: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MaterialRequestUpdate(BaseModel):
    status: str = Field(..., description="Target status: APPROVED, REJECTED, or FULFILLED")
    notes: Optional[str] = None


class MaterialRequestApprove(BaseModel):
    notes: Optional[str] = None


class MaterialRequestReject(BaseModel):
    reason: str = Field(..., min_length=1, max_length=255, description="Mandatory rationale for rejecting requisition")
    notes: Optional[str] = None


class MaterialRequestIssue(BaseModel):
    warehouse_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    notes: Optional[str] = None


# ------------------------------------------------------------------------------
# Employee Operation Request Payloads (Phase 13.2)
# ------------------------------------------------------------------------------

class ConsumeMaterialRequest(BaseModel):
    work_order_id: str
    product_id: str
    quantity: float = Field(..., gt=0.0)
    unit_of_measure: Optional[str] = "kg"
    reason: Optional[str] = "Production assembly"
    notes: Optional[str] = None
    idempotency_key: Optional[str] = None


class ReturnMaterialRequest(BaseModel):
    work_order_id: str
    product_id: str
    quantity: float = Field(..., gt=0.0)
    unit_of_measure: Optional[str] = "kg"
    reason: Optional[str] = "Surplus material returned"
    notes: Optional[str] = None
    idempotency_key: Optional[str] = None


class WastageMaterialRequest(BaseModel):
    work_order_id: str
    product_id: str
    quantity: float = Field(..., gt=0.0)
    unit_of_measure: Optional[str] = "kg"
    reason: str = Field(..., min_length=2, description="Mandatory scrap/wastage rationale")
    notes: Optional[str] = None
    idempotency_key: Optional[str] = None


# ------------------------------------------------------------------------------
# Work Order Detail & Dashboard Stats (Phase 13.2)
# ------------------------------------------------------------------------------

class WorkOrderDetailResponse(WorkOrderResponse):
    product_id: Optional[str] = None
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    production_order_number: Optional[str] = None
    assigned_user_name: Optional[str] = None
    warehouse_code: Optional[str] = None
    materials: List[MaterialRequirementResponse] = []


class EmployeeDashboardStats(BaseModel):
    active_work_orders: int = 0
    materials_in_holding: int = 0
    today_consumed_qty: float = 0.0
    today_returned_qty: float = 0.0
    today_wastage_qty: float = 0.0
    unit: str = "kg / units"
