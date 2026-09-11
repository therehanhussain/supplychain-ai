"""Manufacturing entities repositories (ProductionOrder, WorkOrder, MaterialRequirement)."""
from typing import Optional, Sequence, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.production_order import ProductionOrder
from backend.app.models.work_order import WorkOrder
from backend.app.models.material_requirement import MaterialRequirement
from backend.app.repositories.base import BaseRepository


class ProductionOrderRepository(BaseRepository[ProductionOrder]):
    def __init__(self, session: AsyncSession):
        super().__init__(ProductionOrder, session)

    async def get_by_id_and_org(
        self, order_id: str, organization_id: str
    ) -> Optional[ProductionOrder]:
        result = await self.session.execute(
            select(ProductionOrder)
            .options(
                selectinload(ProductionOrder.product),
                selectinload(ProductionOrder.work_orders),
                selectinload(ProductionOrder.material_requirements),
            )
            .where(
                ProductionOrder.id == order_id,
                ProductionOrder.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self, organization_id: str, status: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> Sequence[ProductionOrder]:
        query = (
            select(ProductionOrder)
            .options(selectinload(ProductionOrder.product))
            .where(ProductionOrder.organization_id == organization_id)
        )
        if status:
            query = query.where(ProductionOrder.status == status)
        query = query.order_by(ProductionOrder.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()


class WorkOrderRepository(BaseRepository[WorkOrder]):
    def __init__(self, session: AsyncSession):
        super().__init__(WorkOrder, session)

    async def get_by_id_and_org(
        self, work_order_id: str, organization_id: str
    ) -> Optional[WorkOrder]:
        result = await self.session.execute(
            select(WorkOrder)
            .options(
                selectinload(WorkOrder.production_order),
                selectinload(WorkOrder.assigned_user),
                selectinload(WorkOrder.material_requirements),
            )
            .where(
                WorkOrder.id == work_order_id,
                WorkOrder.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: str,
        production_order_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[WorkOrder]:
        query = (
            select(WorkOrder)
            .options(selectinload(WorkOrder.production_order))
            .where(WorkOrder.organization_id == organization_id)
        )
        if production_order_id:
            query = query.where(WorkOrder.production_order_id == production_order_id)
        if status:
            query = query.where(WorkOrder.status == status)
        query = query.order_by(WorkOrder.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()


class MaterialRequirementRepository(BaseRepository[MaterialRequirement]):
    def __init__(self, session: AsyncSession):
        super().__init__(MaterialRequirement, session)

    async def get_by_id_and_org(
        self, req_id: str, organization_id: str
    ) -> Optional[MaterialRequirement]:
        result = await self.session.execute(
            select(MaterialRequirement)
            .options(selectinload(MaterialRequirement.product))
            .where(
                MaterialRequirement.id == req_id,
                MaterialRequirement.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_by_work_order_and_product(
        self, organization_id: str, work_order_id: str, product_id: str
    ) -> Optional[MaterialRequirement]:
        result = await self.session.execute(
            select(MaterialRequirement).where(
                MaterialRequirement.organization_id == organization_id,
                MaterialRequirement.work_order_id == work_order_id,
                MaterialRequirement.product_id == product_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        organization_id: str,
        work_order_id: Optional[str] = None,
        production_order_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[MaterialRequirement]:
        query = (
            select(MaterialRequirement)
            .options(selectinload(MaterialRequirement.product))
            .where(MaterialRequirement.organization_id == organization_id)
        )
        if work_order_id:
            query = query.where(MaterialRequirement.work_order_id == work_order_id)
        if production_order_id:
            query = query.where(MaterialRequirement.production_order_id == production_order_id)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
