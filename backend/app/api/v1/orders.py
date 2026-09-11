"""Orders API Endpoints (/api/v1/orders) backed by PostgreSQL persistence."""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.api.dependencies import get_tenant_context, TenantContext
from backend.app.services.order_service import OrderService
from backend.app.schemas.order import OrderResponse, OrderCreate

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", response_model=List[OrderResponse], summary="List purchase orders")
async def list_orders(
    response: Response,
    status: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    page_size: Optional[int] = Query(None, ge=1, le=500, description="Page size limit"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve purchase and sales orders for current tenant."""
    effective_limit = page_size if page_size is not None else limit
    effective_skip = ((page - 1) * effective_limit) if page is not None else skip

    service = OrderService(db, tenant.organization_id)
    orders = await service.list_orders(
        status=status, supplier_id=supplier_id, skip=effective_skip, limit=effective_limit
    )

    response.headers["X-Total-Count"] = str(len(orders))
    response.headers["X-Page"] = str(page or ((skip // effective_limit) + 1))
    response.headers["X-Page-Size"] = str(effective_limit)
    return orders


@router.get("/{order_id}", response_model=OrderResponse, summary="Get order details")
async def get_order(
    order_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a specific order by ID."""
    service = OrderService(db, tenant.organization_id)
    return await service.get_order(order_id)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create purchase order",
)
async def create_order(
    payload: OrderCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Submit and store a new purchase order under current tenant."""
    service = OrderService(db, tenant.organization_id)
    return await service.create_order(payload)


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete order",
)
async def delete_order(
    order_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Delete an order belonging to current tenant."""
    service = OrderService(db, tenant.organization_id)
    await service.delete_order(order_id)
