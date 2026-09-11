"""Shipment domain service executing real persistence and logistics tracking."""
import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.shipment import Shipment
from backend.app.models.order import Order
from backend.app.models.supplier import Supplier
from backend.app.repositories.shipments import ShipmentRepository
from backend.app.schemas.shipment import ShipmentCreate, ShipmentResponse
from backend.app.core.exceptions import AppException


class ShipmentService:
    def __init__(self, db: AsyncSession, organization_id: str):
        self.db = db
        self.organization_id = organization_id
        self.repo = ShipmentRepository(db)

    async def list_shipments(
        self,
        status: Optional[str] = None,
        carrier: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ShipmentResponse]:
        """List tenant-owned shipments."""
        shipments = await self.repo.list_by_org(
            organization_id=self.organization_id,
            status=status,
            carrier=carrier,
            skip=skip,
            limit=limit,
        )
        return [
            ShipmentResponse(
                id=s.id,
                order_id=s.order.order_number if s.order else s.order_id,
                carrier=s.carrier,
                tracking_number=s.tracking_number,
                origin=s.origin or "Origin Facility",
                destination=s.destination or "Destination Hub",
                status=s.status,
                estimated_delivery=s.estimated_delivery,
                created_at=s.created_at,
            )
            for s in shipments
        ]

    async def get_shipment(self, shipment_id: str) -> ShipmentResponse:
        """Fetch shipment ensuring tenant ownership."""
        s = await self.repo.get_by_id_and_org(shipment_id, self.organization_id)
        if not s:
            raise AppException(
                message=f"Shipment '{shipment_id}' not found.",
                status_code=404,
                error_code="SHIPMENT_NOT_FOUND",
            )
        return ShipmentResponse(
            id=s.id,
            order_id=s.order.order_number if s.order else s.order_id,
            carrier=s.carrier,
            tracking_number=s.tracking_number,
            origin=s.origin or "Origin Facility",
            destination=s.destination or "Destination Hub",
            status=s.status,
            estimated_delivery=s.estimated_delivery,
            created_at=s.created_at,
        )

    async def create_shipment(self, payload: ShipmentCreate) -> ShipmentResponse:
        """Create new shipment linked to order."""
        # Find order or create stub
        ord_res = await self.db.execute(
            select(Order).where(
                Order.organization_id == self.organization_id,
                Order.id == payload.order_id,
            )
        )
        order = ord_res.scalar_one_or_none()
        if not order:
            ord_num_res = await self.db.execute(
                select(Order).where(
                    Order.organization_id == self.organization_id,
                    Order.order_number == payload.order_id,
                )
            )
            order = ord_num_res.scalar_one_or_none()

        if not order:
            # Create order to anchor shipment
            supp_res = await self.db.execute(
                select(Supplier).where(Supplier.organization_id == self.organization_id)
            )
            supplier = supp_res.scalars().first()
            if not supplier:
                supplier = Supplier(
                    organization_id=self.organization_id,
                    name="Default Supplier",
                    tier=1,
                )
                self.db.add(supplier)
                await self.db.flush()

            order = Order(
                organization_id=self.organization_id,
                supplier_id=supplier.id,
                order_number=payload.order_id or f"ORD-{uuid.uuid4().hex[:8].upper()}",
                status="shipped",
            )
            self.db.add(order)
            await self.db.flush()

        tracking_num = payload.tracking_number or f"TRK-{uuid.uuid4().hex[:10].upper()}"
        shipment = Shipment(
            organization_id=self.organization_id,
            order_id=order.id,
            tracking_number=tracking_num,
            carrier=payload.carrier,
            origin=payload.origin,
            destination=payload.destination,
            status=payload.status,
            estimated_delivery=payload.estimated_delivery,
        )
        created = await self.repo.create(shipment)
        loaded = await self.repo.get_by_id_and_org(created.id, self.organization_id)

        return ShipmentResponse(
            id=loaded.id,
            order_id=loaded.order.order_number,
            carrier=loaded.carrier,
            tracking_number=loaded.tracking_number,
            origin=loaded.origin or "Origin Facility",
            destination=loaded.destination or "Destination Hub",
            status=loaded.status,
            estimated_delivery=loaded.estimated_delivery,
            created_at=loaded.created_at,
        )

    async def delete_shipment(self, shipment_id: str) -> bool:
        """Delete shipment ensuring tenant ownership."""
        deleted = await self.repo.delete_by_id_and_org(shipment_id, self.organization_id)
        if not deleted:
            raise AppException(
                message=f"Shipment '{shipment_id}' not found.",
                status_code=404,
                error_code="SHIPMENT_NOT_FOUND",
            )
        return True
