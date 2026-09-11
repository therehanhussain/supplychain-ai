"""Shipments API Endpoints (/api/v1/shipments) backed by PostgreSQL persistence."""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.api.dependencies import get_tenant_context, TenantContext
from backend.app.services.shipment_service import ShipmentService
from backend.app.schemas.shipment import ShipmentResponse, ShipmentCreate

router = APIRouter(prefix="/shipments", tags=["Shipments"])


@router.get("", response_model=List[ShipmentResponse], summary="List shipments")
async def list_shipments(
    status: Optional[str] = Query(None),
    carrier: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve logistics shipments and tracking telemetry for current tenant."""
    service = ShipmentService(db, tenant.organization_id)
    return await service.list_shipments(
        status=status, carrier=carrier, skip=skip, limit=limit
    )


@router.get("/{shipment_id}", response_model=ShipmentResponse, summary="Get shipment")
async def get_shipment(
    shipment_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a specific shipment entity."""
    service = ShipmentService(db, tenant.organization_id)
    return await service.get_shipment(shipment_id)


@router.post(
    "",
    response_model=ShipmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create shipment dispatch",
)
async def create_shipment(
    payload: ShipmentCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Dispatch and track a new shipment under current tenant."""
    service = ShipmentService(db, tenant.organization_id)
    return await service.create_shipment(payload)


@router.delete(
    "/{shipment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete shipment",
)
async def delete_shipment(
    shipment_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Delete a shipment record belonging to current tenant."""
    service = ShipmentService(db, tenant.organization_id)
    await service.delete_shipment(shipment_id)
