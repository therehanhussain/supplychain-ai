"""Shipment repository with real-time tracking and tenant isolation."""
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.shipment import Shipment
from backend.app.repositories.base import BaseRepository


class ShipmentRepository(BaseRepository[Shipment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Shipment, session)

    async def get_by_id_and_org(
        self, shipment_id: str, organization_id: str
    ) -> Optional[Shipment]:
        """Fetch shipment with loaded order reference, tenant-scoped."""
        result = await self.session.execute(
            select(Shipment)
            .options(selectinload(Shipment.order))
            .where(
                Shipment.id == shipment_id,
                Shipment.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_tracking_number_and_org(
        self, tracking_number: str, organization_id: str
    ) -> Optional[Shipment]:
        """Fetch shipment by unique tracking number within organization."""
        result = await self.session.execute(
            select(Shipment)
            .options(selectinload(Shipment.order))
            .where(
                Shipment.tracking_number == tracking_number,
                Shipment.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: str,
        status: Optional[str] = None,
        carrier: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Shipment]:
        """List shipments belonging to organization with optional status filter."""
        query = (
            select(Shipment)
            .options(selectinload(Shipment.order))
            .where(Shipment.organization_id == organization_id)
        )
        if status:
            query = query.where(Shipment.status == status)
        if carrier:
            query = query.where(Shipment.carrier == carrier)
        query = query.order_by(Shipment.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    list_by_tenant = list_by_org
    get_by_id_and_tenant = get_by_id_and_org


    async def delete_by_id_and_org(
        self, shipment_id: str, organization_id: str
    ) -> bool:
        """Delete shipment ensuring tenant ownership."""
        shipment = await self.get_by_id_and_org(shipment_id, organization_id)
        if shipment:
            await self.session.delete(shipment)
            await self.session.commit()
            return True
        return False
