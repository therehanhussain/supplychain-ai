"""Inventory API Endpoints (/api/v1/inventory) backed by PostgreSQL persistence."""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.api.dependencies import get_tenant_context, TenantContext
from backend.app.services.inventory_service import InventoryService
from backend.app.schemas.inventory import InventoryItemResponse, InventoryItemCreate

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("", response_model=List[InventoryItemResponse], summary="List inventory items")
async def list_inventory(
    warehouse_id: Optional[str] = Query(None),
    low_stock_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve catalog of inventory items and stock levels for current tenant."""
    service = InventoryService(db, tenant.organization_id)
    return await service.list_inventory(
        warehouse_id=warehouse_id,
        low_stock_only=low_stock_only,
        skip=skip,
        limit=limit,
    )


@router.get("/{item_id}", response_model=InventoryItemResponse, summary="Get inventory item")
async def get_inventory_item(
    item_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a specific inventory SKU item."""
    service = InventoryService(db, tenant.organization_id)
    return await service.get_inventory(item_id)


@router.post(
    "",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or restock inventory item",
)
async def create_inventory_item(
    payload: InventoryItemCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Add a new item to warehouse inventory under current tenant."""
    service = InventoryService(db, tenant.organization_id)
    return await service.create_inventory(payload)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete inventory item",
)
async def delete_inventory_item(
    item_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Delete an inventory record belonging to current tenant."""
    service = InventoryService(db, tenant.organization_id)
    await service.delete_inventory(item_id)
