"""Inventory repository with warehouse/product relationships and tenant scoping."""
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.inventory import Inventory
from backend.app.repositories.base import BaseRepository


class InventoryRepository(BaseRepository[Inventory]):
    def __init__(self, session: AsyncSession):
        super().__init__(Inventory, session)

    async def get_by_id_and_org(
        self, inventory_id: str, organization_id: str
    ) -> Optional[Inventory]:
        """Fetch inventory item with loaded product and warehouse, tenant-scoped."""
        result = await self.session.execute(
            select(Inventory)
            .options(selectinload(Inventory.product), selectinload(Inventory.warehouse))
            .where(
                Inventory.id == inventory_id,
                Inventory.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: str,
        warehouse_id: Optional[str] = None,
        low_stock_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Inventory]:
        """List inventory records belonging strictly to an organization."""
        query = (
            select(Inventory)
            .options(selectinload(Inventory.product), selectinload(Inventory.warehouse))
            .where(Inventory.organization_id == organization_id)
        )
        if warehouse_id:
            query = query.where(Inventory.warehouse_id == warehouse_id)
        if low_stock_only:
            query = query.where(Inventory.quantity <= Inventory.safety_stock)
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    list_by_tenant = list_by_org
    get_by_id_and_tenant = get_by_id_and_org


    async def delete_by_id_and_org(
        self, inventory_id: str, organization_id: str
    ) -> bool:
        """Delete inventory record ensuring tenant ownership."""
        item = await self.get_by_id_and_org(inventory_id, organization_id)
        if item:
            await self.session.delete(item)
            await self.session.commit()
            return True
        return False
