"""Manufacturing & Material Traceability Endpoints (/api/v1/...)."""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.api.dependencies import get_tenant_context, get_auth_tenant_context, TenantContext
from backend.app.services.material_service import MaterialTraceabilityService
from backend.app.repositories.stock_transaction import StockTransactionRepository
from backend.app.models.enums import TransactionType
from backend.app.models.user import UserRole
from backend.app.schemas.manufacturing import (
    ProductionOrderCreate,
    ProductionOrderResponse,
    WorkOrderCreate,
    WorkOrderResponse,
    MaterialRequirementCreate,
    MaterialRequirementResponse,
    StockTransactionCreate,
    StockTransactionResponse,
    StockTransferCreate,
    TraceabilityTimelineResponse,
    MaterialRequestCreate,
    MaterialRequestResponse,
    MaterialRequestUpdate,
    MaterialRequestApprove,
    MaterialRequestReject,
    MaterialRequestIssue,
    ConsumeMaterialRequest,
    ReturnMaterialRequest,
    WastageMaterialRequest,
    WorkOrderDetailResponse,
    EmployeeDashboardStats,
)

router = APIRouter(tags=["Manufacturing & Material Traceability"])


# ------------------------------------------------------------------------------
# Production Orders
# ------------------------------------------------------------------------------
@router.post(
    "/production-orders",
    response_model=ProductionOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create production order for finished goods",
)
async def create_production_order(
    payload: ProductionOrderCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.create_production_order(payload)


@router.get(
    "/production-orders",
    response_model=List[ProductionOrderResponse],
    summary="List tenant production orders",
)
async def list_production_orders(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.list_production_orders(status=status, skip=skip, limit=limit)


# ------------------------------------------------------------------------------
# Work Orders
# ------------------------------------------------------------------------------
@router.post(
    "/work-orders",
    response_model=WorkOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create discrete work order under production order",
)
async def create_work_order(
    payload: WorkOrderCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.create_work_order(payload)


@router.get(
    "/work-orders",
    response_model=List[WorkOrderResponse],
    summary="List tenant work orders",
)
async def list_work_orders(
    production_order_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.list_work_orders(
        production_order_id=production_order_id, status=status, skip=skip, limit=limit
    )


# ------------------------------------------------------------------------------
# Material Requirements
# ------------------------------------------------------------------------------
@router.post(
    "/material-requirements",
    response_model=MaterialRequirementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register required raw materials for work order or production order",
)
async def create_material_requirement(
    payload: MaterialRequirementCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.create_material_requirement(payload)


# ------------------------------------------------------------------------------
# Stock Transactions & Material Movements
# ------------------------------------------------------------------------------
@router.post(
    "/stock-transactions",
    response_model=StockTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record atomic stock movement (Receipt, Issue, Consumption, Return, Wastage, etc.)",
)
async def record_stock_transaction(
    payload: StockTransactionCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.record_transaction(payload)


@router.get(
    "/stock-transactions",
    response_model=List[StockTransactionResponse],
    summary="List material transactions across tenant facilities",
)
async def list_stock_transactions(
    inventory_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    warehouse_id: Optional[str] = Query(None),
    work_order_id: Optional[str] = Query(None),
    production_order_id: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    repo = StockTransactionRepository(db)
    items = await repo.list_by_org(
        organization_id=tenant.organization_id,
        inventory_id=inventory_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        work_order_id=work_order_id,
        production_order_id=production_order_id,
        transaction_type=transaction_type,
        skip=skip,
        limit=limit,
    )
    return [
        StockTransactionResponse(
            id=tx.id,
            organization_id=tx.organization_id,
            inventory_id=tx.inventory_id,
            product_id=tx.product_id,
            product_sku=tx.product.sku if tx.product else None,
            product_name=tx.product.name if tx.product else None,
            warehouse_id=tx.warehouse_id,
            warehouse_code=tx.warehouse.code if tx.warehouse else None,
            work_order_id=tx.work_order_id,
            production_order_id=tx.production_order_id,
            employee_id=tx.employee_id,
            employee_name=tx.employee.full_name if tx.employee else None,
            performed_by_user_id=tx.performed_by_user_id,
            performed_by_name=tx.performed_by_user.full_name if tx.performed_by_user else "User",
            transaction_type=tx.transaction_type,
            quantity=tx.quantity,
            unit_of_measure=tx.unit_of_measure,
            reason=tx.reason,
            source_location=tx.source_location,
            destination_location=tx.destination_location,
            reference_type=tx.reference_type,
            reference_id=tx.reference_id,
            notes=tx.notes,
            created_at=tx.created_at,
        )
        for tx in items
    ]


@router.get(
    "/inventory/{inventory_id}/transactions",
    response_model=List[StockTransactionResponse],
    summary="Get chronological material ledger for specific inventory record",
)
async def get_inventory_transactions(
    inventory_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    repo = StockTransactionRepository(db)
    items = await repo.list_by_org(
        organization_id=tenant.organization_id,
        inventory_id=inventory_id,
        skip=skip,
        limit=limit,
    )
    return [
        StockTransactionResponse(
            id=tx.id,
            organization_id=tx.organization_id,
            inventory_id=tx.inventory_id,
            product_id=tx.product_id,
            product_sku=tx.product.sku if tx.product else None,
            product_name=tx.product.name if tx.product else None,
            warehouse_id=tx.warehouse_id,
            warehouse_code=tx.warehouse.code if tx.warehouse else None,
            work_order_id=tx.work_order_id,
            production_order_id=tx.production_order_id,
            employee_id=tx.employee_id,
            employee_name=tx.employee.full_name if tx.employee else None,
            performed_by_user_id=tx.performed_by_user_id,
            performed_by_name=tx.performed_by_user.full_name if tx.performed_by_user else "User",
            transaction_type=tx.transaction_type,
            quantity=tx.quantity,
            unit_of_measure=tx.unit_of_measure,
            reason=tx.reason,
            source_location=tx.source_location,
            destination_location=tx.destination_location,
            reference_type=tx.reference_type,
            reference_id=tx.reference_id,
            notes=tx.notes,
            created_at=tx.created_at,
        )
        for tx in items
    ]


@router.post(
    "/stock-transfers",
    summary="Execute atomic inter-warehouse material transfer",
)
async def transfer_stock(
    payload: StockTransferCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    out_tx, in_tx = await service.transfer_stock(payload)
    return {
        "status": "success",
        "message": f"Successfully transferred {payload.quantity} {payload.unit_of_measure} from {payload.source_warehouse_id} to {payload.destination_warehouse_id}.",
        "outbound_transaction_id": out_tx.id,
        "inbound_transaction_id": in_tx.id,
    }


# ------------------------------------------------------------------------------
# Material Traceability Timeline
# ------------------------------------------------------------------------------
@router.get(
    "/materials/{product_id}/traceability",
    response_model=TraceabilityTimelineResponse,
    summary="Get complete lifecycle traceability timeline for a raw material or product",
)
async def get_material_traceability(
    product_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.get_material_traceability(product_id)

# ------------------------------------------------------------------------------
# Phase 13.2: Employee Operations Endpoints
# ------------------------------------------------------------------------------

@router.get(
    "/my-work-orders",
    response_model=List[WorkOrderDetailResponse],
    summary="Get work orders assigned to the current employee",
)
async def get_my_work_orders(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tenant: TenantContext = Depends(get_auth_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.get_my_work_orders(status=status, skip=skip, limit=limit)


@router.get(
    "/work-orders/{id}",
    response_model=WorkOrderDetailResponse,
    summary="Get detailed view of a specific work order",
)
async def get_work_order_detail(
    id: str,
    tenant: TenantContext = Depends(get_auth_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    is_admin = tenant.role in (UserRole.ADMIN, "ADMIN")
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.get_work_order_details(work_order_id=id, is_admin=is_admin)


@router.get(
    "/work-orders/{id}/materials",
    response_model=List[MaterialRequirementResponse],
    summary="List required materials and current holding for a work order",
)
async def get_work_order_materials(
    id: str,
    tenant: TenantContext = Depends(get_auth_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    is_admin = tenant.role in (UserRole.ADMIN, "ADMIN")
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.get_work_order_materials(work_order_id=id, is_admin=is_admin)


@router.get(
    "/employee/dashboard-stats",
    response_model=EmployeeDashboardStats,
    summary="Get aggregated operational KPIs for current employee",
)
async def get_employee_dashboard_stats(
    tenant: TenantContext = Depends(get_auth_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.get_employee_dashboard_stats()


@router.get(
    "/employee/activity",
    response_model=List[StockTransactionResponse],
    summary="Get transaction activity log for current employee",
)
async def get_employee_activity(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: TenantContext = Depends(get_auth_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.get_employee_activity(skip=skip, limit=limit)


@router.post(
    "/material-requests",
    response_model=MaterialRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Employee submits request for additional raw material",
)
async def create_material_request(
    payload: MaterialRequestCreate,
    tenant: TenantContext = Depends(get_auth_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.create_material_request(payload)


@router.get(
    "/material-requests",
    response_model=List[MaterialRequestResponse],
    summary="List material requests for work order or employee",
)
async def list_material_requests(
    work_order_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    my_requests: bool = Query(False),
    tenant: TenantContext = Depends(get_auth_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    is_admin = tenant.role in (UserRole.ADMIN, "ADMIN")
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.list_material_requests(
        work_order_id=work_order_id,
        status=status,
        my_requests_only=(my_requests or not is_admin),
    )


@router.get(
    "/material-requests/{id}",
    response_model=MaterialRequestResponse,
    summary="Get single material request with inventory context",
)
async def get_material_request(
    id: str,
    tenant: TenantContext = Depends(get_auth_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.get_material_request(id)


@router.post(
    "/material-requests/{id}/approve",
    response_model=MaterialRequestResponse,
    summary="Approve pending material request (Admin/Storekeeper)",
)
async def approve_material_request(
    id: str,
    payload: Optional[MaterialRequestApprove] = None,
    tenant: TenantContext = Depends(get_auth_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.approve_material_request(id, payload)


@router.post(
    "/material-requests/{id}/reject",
    response_model=MaterialRequestResponse,
    summary="Reject pending material request with reason (Admin/Storekeeper)",
)
async def reject_material_request(
    id: str,
    payload: MaterialRequestReject,
    tenant: TenantContext = Depends(get_auth_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.reject_material_request(id, payload)


@router.post(
    "/material-requests/{id}/issue",
    response_model=StockTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue material from warehouse to work order against approved request (Admin/Storekeeper)",
)
async def issue_material_request(
    id: str,
    payload: Optional[MaterialRequestIssue] = None,
    tenant: TenantContext = Depends(get_auth_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    return await service.issue_material_request(id, payload)


@router.post(
    "/transactions/consume",
    response_model=StockTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Operator consumes material from work order holding",
)
async def consume_material(
    payload: ConsumeMaterialRequest,
    tenant: TenantContext = Depends(get_auth_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    tx_payload = StockTransactionCreate(
        work_order_id=payload.work_order_id,
        product_id=payload.product_id,
        transaction_type=TransactionType.CONSUMPTION,
        quantity=payload.quantity,
        unit_of_measure=payload.unit_of_measure,
        reason=payload.reason or "Production assembly",
        notes=payload.notes,
        reference_id=payload.idempotency_key,
    )
    return await service.record_transaction(tx_payload)


@router.post(
    "/transactions/return",
    response_model=StockTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Operator returns surplus material from holding to warehouse",
)
async def return_material(
    payload: ReturnMaterialRequest,
    tenant: TenantContext = Depends(get_auth_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    tx_payload = StockTransactionCreate(
        work_order_id=payload.work_order_id,
        product_id=payload.product_id,
        transaction_type=TransactionType.RETURN,
        quantity=payload.quantity,
        unit_of_measure=payload.unit_of_measure,
        reason=payload.reason or "Surplus material returned",
        notes=payload.notes,
        reference_id=payload.idempotency_key,
    )
    return await service.record_transaction(tx_payload)


@router.post(
    "/transactions/waste",
    response_model=StockTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Operator reports scrap or wastage from work order holding",
)
async def report_wastage(
    payload: WastageMaterialRequest,
    tenant: TenantContext = Depends(get_auth_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    service = MaterialTraceabilityService(db, tenant.organization_id, tenant.user_id)
    tx_payload = StockTransactionCreate(
        work_order_id=payload.work_order_id,
        product_id=payload.product_id,
        transaction_type=TransactionType.WASTAGE,
        quantity=payload.quantity,
        unit_of_measure=payload.unit_of_measure,
        reason=payload.reason,
        notes=payload.notes,
        reference_id=payload.idempotency_key,
    )
    return await service.record_transaction(tx_payload)
