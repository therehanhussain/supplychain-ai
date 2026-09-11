"""Supplier repository with strict organization tenant isolation."""
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.supplier import Supplier
from backend.app.repositories.base import BaseRepository


class SupplierRepository(BaseRepository[Supplier]):
    def __init__(self, session: AsyncSession):
        super().__init__(Supplier, session)

    async def get_by_id_and_org(
        self, supplier_id: str, organization_id: str
    ) -> Optional[Supplier]:
        """Fetch supplier scoped to organization."""
        result = await self.session.execute(
            select(Supplier).where(
                Supplier.id == supplier_id,
                Supplier.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: str,
        tier: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Supplier]:
        """List suppliers belonging to an organization with optional filtering."""
        query = select(Supplier).where(Supplier.organization_id == organization_id)
        if tier is not None:
            query = query.where(Supplier.tier == tier)
        if status:
            query = query.where(Supplier.status == status)
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    list_by_tenant = list_by_org
    get_by_id_and_tenant = get_by_id_and_org


    async def delete_by_id_and_org(
        self, supplier_id: str, organization_id: str
    ) -> bool:
        """Delete supplier ensuring organization ownership."""
        supplier = await self.get_by_id_and_org(supplier_id, organization_id)
        if supplier:
            await self.session.delete(supplier)
            await self.session.commit()
            return True
        return False
