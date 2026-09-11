"""Suppliers API Endpoints (/api/v1/suppliers) backed by PostgreSQL persistence."""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.api.dependencies import get_tenant_context, TenantContext
from backend.app.services.supplier_service import SupplierService
from backend.app.schemas.supplier import SupplierResponse, SupplierCreate, SupplierUpdate


router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.get("", response_model=List[SupplierResponse], summary="List all suppliers")
async def list_suppliers(
    response: Response,
    tier: Optional[int] = Query(None, ge=1, le=4),
    status: Optional[str] = Query(None),
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    page_size: Optional[int] = Query(None, ge=1, le=500, description="Page size limit"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve catalog of all registered supply chain vendors for current tenant."""
    effective_limit = page_size if page_size is not None else limit
    effective_skip = ((page - 1) * effective_limit) if page is not None else skip

    service = SupplierService(db, tenant.organization_id)
    suppliers = await service.list_suppliers(tier=tier, status=status, skip=effective_skip, limit=effective_limit)

    response.headers["X-Total-Count"] = str(len(suppliers))
    response.headers["X-Page"] = str(page or ((skip // effective_limit) + 1))
    response.headers["X-Page-Size"] = str(effective_limit)
    return suppliers


@router.get("/{supplier_id}", response_model=SupplierResponse, summary="Get supplier details")
async def get_supplier(
    supplier_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a specific supplier entity with tenant isolation."""
    service = SupplierService(db, tenant.organization_id)
    return await service.get_supplier(supplier_id)


@router.post(
    "",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new supplier",
)
async def create_supplier(
    payload: SupplierCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Register a new supplier in the network under the tenant's organization."""
    service = SupplierService(db, tenant.organization_id)
    return await service.create_supplier(payload)


@router.put(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Update supplier details",
)
async def update_supplier(
    supplier_id: str,
    payload: SupplierUpdate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Update supplier information under tenant ownership."""
    service = SupplierService(db, tenant.organization_id)
    return await service.update_supplier(supplier_id, payload)


@router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete supplier",
)
async def delete_supplier(
    supplier_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Delete a supplier belonging to the tenant."""
    service = SupplierService(db, tenant.organization_id)
    await service.delete_supplier(supplier_id)

