"""Order repository with item eager-loading and organization tenant isolation."""
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.order import Order, OrderItem
from backend.app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)

    async def get_by_id_and_org(
        self, order_id: str, organization_id: str
    ) -> Optional[Order]:
        """Fetch order with loaded supplier and line items, tenant-scoped."""
        result = await self.session.execute(
            select(Order)
            .options(
                selectinload(Order.supplier),
                selectinload(Order.items).selectinload(OrderItem.product),
            )
            .where(
                Order.id == order_id,
                Order.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_order_number_and_org(
        self, order_number: str, organization_id: str
    ) -> Optional[Order]:
        """Fetch order by unique order number within organization."""
        result = await self.session.execute(
            select(Order)
            .options(
                selectinload(Order.supplier),
                selectinload(Order.items).selectinload(OrderItem.product),
            )
            .where(
                Order.order_number == order_number,
                Order.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: str,
        status: Optional[str] = None,
        supplier_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Order]:
        """List orders belonging to organization with optional status filter."""
        query = (
            select(Order)
            .options(
                selectinload(Order.supplier),
                selectinload(Order.items).selectinload(OrderItem.product),
            )
            .where(Order.organization_id == organization_id)
        )
        if status:
            query = query.where(Order.status == status)
        if supplier_id:
            query = query.where(Order.supplier_id == supplier_id)
        query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    list_by_tenant = list_by_org
    get_by_id_and_tenant = get_by_id_and_org


    async def delete_by_id_and_org(
        self, order_id: str, organization_id: str
    ) -> bool:
        """Delete order ensuring tenant ownership."""
        order = await self.get_by_id_and_org(order_id, organization_id)
        if order:
            await self.session.delete(order)
            await self.session.commit()
            return True
        return False
